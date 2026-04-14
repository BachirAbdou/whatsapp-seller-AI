// Marche très bien, revenir au cas ou

/*const express = require("express")
const bodyParser = require("body-parser")
const fs = require("fs")
const sellerLastActivity = new Map()
const connectingSellers = new Map()
const MAX_ACTIVE_SESSIONS = 200
const reconnectAttempts = new Map()
const retryCache = new Map()
const MAX_WEBSOCKETS = 300

const {
default: makeWASocket,
useMultiFileAuthState,
DisconnectReason,
fetchLatestBaileysVersion
} = require("@whiskeysockets/baileys")

const P = require("pino")

const app = express()
app.use(bodyParser.json())

const clients = {}
const qrCodes = {}
const qrTimers = {}
const clientStatus = new Map()

const messageQueues = {}
const queueProcessing = {}

const lastMessageTime = new Map()
const lastReplyTime = new Map()

const sellerRateLimit = new Map()

const cluster = require("cluster")
const os = require("os")

//const numCPUs = os.cpus().length
const numCPUs = 1

function activeSessionsCount(){
return Object.keys(clients).length
}

setInterval(() => {

const now = Date.now()

for(const seller_id in clients){

const client = clients[seller_id]

if(
    (!client?.ws || client.ws.readyState !== 1) &&
    clientStatus.get(seller_id) !== "connecting" &&
    clientStatus.get(seller_id) !== "qr_waiting"
){

console.log("Socket mort nettoyage", seller_id)

try{
client?.end()
client?.ev?.removeAllListeners()
}catch(e){}

delete clients[seller_id]
delete messageQueues[seller_id]
delete queueProcessing[seller_id]

clientStatus.set(seller_id,"disconnected")

}

const last = sellerLastActivity.get(seller_id) || 0

if(
    now - last > 1000 * 60 * 5 &&
    clientStatus.get(seller_id) === "connected"
){

const queue = messageQueues[seller_id]

if(!queue || queue.length === 0){

console.log("Fermeture session inactive", seller_id)

const c = clients[seller_id]

if(c){
c.end()
c.ev.removeAllListeners()
}

delete clients[seller_id]
delete messageQueues[seller_id]
delete queueProcessing[seller_id]

sellerLastActivity.delete(seller_id)

clientStatus.set(seller_id,"disconnected")

}

}

}

if(lastMessageTime.size > 10000){
lastMessageTime.clear()
}

if(lastReplyTime.size > 10000){
lastReplyTime.clear()
}

if(sellerRateLimit.size > 10000){
sellerRateLimit.clear()
}

console.log("Nettoyage mémoire des maps")

}, 1000 * 60)

if (cluster.isPrimary) {

console.log("Master process")

for (let i = 0; i < numCPUs; i++) {
cluster.fork()
}

cluster.on("exit", () => {
console.log("Worker mort, restart")
cluster.fork()
})

}

process.on("uncaughtException", err => {
console.log("UNCAUGHT ERROR", err)
})

process.on("unhandledRejection", err => {
console.log("UNHANDLED PROMISE", err)
})

async function connectSeller(seller_id){

if(activeSessionsCount() >= MAX_ACTIVE_SESSIONS){

console.log("LIMIT ACTIVE SESSIONS")

return
}

if(activeSessionsCount() >= MAX_WEBSOCKETS){

console.log("MAX WEBSOCKETS atteint")

return

}

if(clients[seller_id] || connectingSellers.get(seller_id)){
return
}

connectingSellers.set(seller_id,true)

console.log("Connexion vendeur", seller_id)

clientStatus.set(seller_id,"connecting")

const { state, saveCreds } =
await useMultiFileAuthState(`sessions/${seller_id}`)

const { version } = await fetchLatestBaileysVersion()

const sock = makeWASocket({

version,
auth: state,
browser: ["AssistantSeller","Chrome","1.0"],
logger: P({ level:"silent" }),

printQRInTerminal:false,

// OPTIMISATION SAAS
syncFullHistory:false,
shouldSyncHistoryMessage: () => false,
markOnlineOnConnect:false,
generateHighQualityLinkPreview:false,

emitOwnEvents:false,
fireInitQueries:false,
//msgRetryCounterCache: retryCache(),

})
sock.seller_id = seller_id

clients[seller_id] = sock

sock.ev.on("creds.update", saveCreds)



sock.ev.on("connection.update", (update)=>{

const {connection,qr,lastDisconnect} = update

if(qr){

qrCodes[seller_id] = qr
updateBotStatus(seller_id,"qr_waiting")

if(qrTimers[seller_id]){
clearTimeout(qrTimers[seller_id])
}

qrTimers[seller_id] = setTimeout(()=>{
delete qrCodes[seller_id]
},600000)

console.log("QR généré pour", seller_id)
}

if(connection === "open"){

updateBotStatus(seller_id,"connected")

console.log("WhatsApp connecté", seller_id)

connectingSellers.delete(seller_id)
reconnectAttempts.delete(seller_id)

clientStatus.set(seller_id,"connected")

}

if(connection === "close"){

updateBotStatus(seller_id,"offline")

console.log("WhatsApp déconnecté", seller_id)

const reason = lastDisconnect?.error
const statusCode =
lastDisconnect?.error?.output?.statusCode

if(statusCode !== 515 && statusCode !== 405){
console.log("RAISON:", lastDisconnect?.error)
}

clientStatus.set(seller_id,"disconnected")

// nettoyage mémoire
delete clients[seller_id]
delete qrCodes[seller_id]
delete messageQueues[seller_id]
delete queueProcessing[seller_id]

const shouldReconnect =
lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut

if(shouldReconnect && !clients[seller_id]){

const attempts = reconnectAttempts.get(seller_id) || 0

if(attempts > 5){
console.log("STOP RECONNECT", seller_id)
return
}

reconnectAttempts.set(seller_id, attempts + 1)

console.log("Reconnexion automatique", seller_id)

setTimeout(()=>{
connectSeller(seller_id)
},5000)

}

}

})

sock.ev.on("messages.upsert", async ({messages,type})=>{

const seller_id = sock.seller_id

if(type !== "notify") return

const msg = messages[0]

if(!msg.message) return

// ignorer vieux messages
const msgTime = msg.messageTimestamp * 1000
const now = Date.now()

if(now - msgTime > 30000){
return
}

const from = msg.key.remoteJid

const text =
msg.message.conversation ||
msg.message.extendedTextMessage?.text ||
msg.message.imageMessage?.caption

//if(!text) return

if(!from) return

if(!text || text.length > 500){
console.log("message trop long ignoré")
return
}

if(from.endsWith("@g.us")) return

console.log("MESSAGE RECU:", text)

sellerLastActivity.set(seller_id, Date.now())

const now2 = Date.now()
const key = seller_id + "_" + from

// anti spam message
if(lastMessageTime.get(key) && now2 - lastMessageTime.get(key) < 2000){
return
}

lastMessageTime.set(key, now2)

// création queue vendeur si nécessaire
if(!messageQueues[seller_id]){
messageQueues[seller_id] = []
}

// limite queue
if(messageQueues[seller_id].length > 50){
console.log("Queue overflow")
return
}

messageQueues[seller_id].push({
msg:{
body:text,
from:from,
notifyName:msg.pushName
}
})

console.log("MESSAGE AJOUTE A LA QUEUE")

processQueue(seller_id)

})

}


async function updateBotStatus(seller_id, status){

try{

await fetch("http://localhost:8000/api/bot_status",{

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({
seller_id: seller_id,
status: status
})

})

}catch(e){

console.log("Erreur update bot status")

}

}

async function restoreSessions(){

if(!fs.existsSync("./sessions")){
fs.mkdirSync("./sessions")
return
}

const sellers = fs.readdirSync("./sessions")

for(const seller_id of sellers){

console.log("Restauration session", seller_id)

connectSeller(seller_id)

}

}

app.post("/connect", async (req,res)=>{

const seller_id = String(req.body.seller_id)

if(clients[seller_id]){
return res.json({message:"Déjà connecté"})
}

await connectSeller(seller_id)

res.json({message:"Connexion lancée"})

})

app.get("/qr/:seller_id",(req,res)=>{

const seller_id = String(req.params.seller_id)

const qr = qrCodes[seller_id]

if(!qr){
return res.json({status:"waiting"})
}

res.json({
status:"qr_ready",
qr:qr
})

})

app.get("/status/:seller_id",(req,res)=>{

const seller_id = String(req.params.seller_id)

const status = clientStatus.get(seller_id) || "disconnected"

res.json({status})

})

app.post("/disconnect/:seller_id",(req,res)=>{

const seller_id = String(req.params.seller_id)

const client = clients[seller_id]

if(client){

client.end()

delete clients[seller_id]
delete qrCodes[seller_id]
delete messageQueues[seller_id]
delete queueProcessing[seller_id]

sellerLastActivity.delete(seller_id)
connectingSellers.delete(seller_id)
reconnectAttempts.delete(seller_id)

clientStatus.set(seller_id,"disconnected")

}

res.json({message:"déconnecté"})

})

async function processQueue(seller_id){

if(!clients[seller_id]){

console.log("Session fermée, reconnexion", seller_id)

await connectSeller(seller_id)

await new Promise(resolve => setTimeout(resolve,6000))

if(!clients[seller_id]){
console.log("Impossible de reconnecter", seller_id)
return
}

}

if(queueProcessing[seller_id]) return

queueProcessing[seller_id] = true

const queue = messageQueues[seller_id]

while(queue && queue.length > 0){

await new Promise(resolve => setImmediate(resolve))

const item = queue.shift()

const { msg } = item

try{

const controller = new AbortController()

setTimeout(()=>controller.abort(),10000)

const rate = sellerRateLimit.get(seller_id) || {
count:0,
time:Date.now()
}

if(Date.now() - rate.time > 60000){
rate.count = 0
rate.time = Date.now()
}

rate.count++

if(rate.count > 30){
console.log("RATE LIMIT vendeur", seller_id)
continue
}

sellerRateLimit.set(seller_id, rate)

console.log("ENVOI A FASTAPI:", msg.body)

let response

try{

response = await fetch(
`http://localhost:8000/whatsapp/${seller_id}`,
{
method:"POST",
headers:{
"Content-Type":"application/json"
},
signal:controller.signal,
body:JSON.stringify({
Body:msg.body,
From:msg.from,
ProfileName:msg.notifyName || "Client"
})
}
)

}catch(err){

console.log("FASTAPI TIMEOUT")

continue

}

const text = await response.text()

if(!text || text.trim()===""){
continue
}

const client = clients[seller_id]

if(!client){
continue
}

const replyKey = seller_id + "_" + msg.from
const now = Date.now()

// anti spam reply
if(lastReplyTime.get(replyKey) && now - lastReplyTime.get(replyKey) < 5000){
continue
}

lastReplyTime.set(replyKey, now)

const delay = Math.floor(Math.random()*2000)+1000
await new Promise(resolve => setTimeout(resolve,delay))

try{

await client.sendMessage(msg.from,{ text:text })

}catch(err){

console.log("SEND ERROR", err)

}

}catch(err){

console.log("message error",err)

}

}

queueProcessing[seller_id] = false

if(messageQueues[seller_id]?.length === 0){
delete messageQueues[seller_id]
}

}

if (!cluster.isPrimary) {

app.listen(3000, async ()=>{

console.log("Worker", cluster.worker.id, "en ligne")

if(cluster.worker.id === 1){
await restoreSessions()
}

})

}
*/


const express = require("express")
const bodyParser = require("body-parser")
const fs = require("fs")
const sellerLastActivity = new Map()
const connectingSellers = new Map()
const MAX_ACTIVE_SESSIONS = 200
const reconnectAttempts = new Map()
const retryCache = new Map()
const MAX_WEBSOCKETS = 300
const MAX_RETRIES = 10

const {
default: makeWASocket,
useMultiFileAuthState,
DisconnectReason,
fetchLatestBaileysVersion
} = require("@whiskeysockets/baileys")

const P = require("pino")

const app = express()
app.use(bodyParser.json())

const clients = {}
const qrCodes = {}
const qrTimers = {}
const clientStatus = new Map()

const messageQueues = {}
const queueProcessing = {}

const lastMessageTime = new Map()
const lastReplyTime = new Map()

const sellerRateLimit = new Map()

const cluster = require("cluster")
const os = require("os")

//const numCPUs = os.cpus().length
const numCPUs = 1

function activeSessionsCount(){
return Object.keys(clients).length
}

async function safeDisconnect(seller_id){

    const client = clients[seller_id]

    if(client){
        try{
            client.end() // ✅ suffisant
            client.ev.removeAllListeners()
        }catch(e){}
    }

    delete clients[seller_id]
    delete qrCodes[seller_id]
    connectingSellers.delete(seller_id)
}

setInterval(() => {

const now = Date.now()

for(const seller_id in clients){

const client = clients[seller_id]

const status = clientStatus.get(seller_id)

if(
    status !== "connected" &&
    status !== "connecting" &&
    status !== "qr_waiting" &&
    status !== "handshake" &&
    status !== "qr_expired"
){
    console.log("Nettoyage session inactive", seller_id)

    try{
        client?.end()
        client?.ev?.removeAllListeners()
    }catch(e){}

    delete clients[seller_id]
    delete messageQueues[seller_id]
    delete queueProcessing[seller_id]

    clientStatus.set(seller_id,"disconnected")
}

const last = sellerLastActivity.get(seller_id) || 0

}

if(lastMessageTime.size > 10000){
lastMessageTime.clear()
}

if(lastReplyTime.size > 10000){
lastReplyTime.clear()
}

if(sellerRateLimit.size > 10000){
sellerRateLimit.clear()
}

console.log("Nettoyage mémoire des maps")

}, 1000 * 60)

if (cluster.isPrimary) {

console.log("Master process")

for (let i = 0; i < numCPUs; i++) {
cluster.fork()
}

cluster.on("exit", () => {
console.log("Worker mort, restart")
cluster.fork()
})

}

process.on("uncaughtException", err => {
console.log("UNCAUGHT ERROR", err)
})

process.on("unhandledRejection", err => {
console.log("UNHANDLED PROMISE", err)
})

async function connectSeller(seller_id){

if(activeSessionsCount() >= MAX_ACTIVE_SESSIONS){

console.log("LIMIT ACTIVE SESSIONS")

return
}

if(activeSessionsCount() >= MAX_WEBSOCKETS){

console.log("MAX WEBSOCKETS atteint")

return

}

if(connectingSellers.get(seller_id)){
    console.log("Déjà en connexion", seller_id)
    return
}

connectingSellers.set(seller_id,true)

console.log("Connexion vendeur", seller_id)

clientStatus.set(seller_id,"connecting")

const { state, saveCreds } =
await useMultiFileAuthState(`sessions/${seller_id}`)

const { version } = await fetchLatestBaileysVersion()

const sock = makeWASocket({

version,
auth: state,
browser: ["AssistantSeller","Chrome","1.0"],
logger: P({ level:"silent" }),

printQRInTerminal:false,

// OPTIMISATION SAAS
syncFullHistory:false,
shouldSyncHistoryMessage: () => false,
markOnlineOnConnect:false,
generateHighQualityLinkPreview:false,

})
sock.seller_id = seller_id

clients[seller_id] = sock

sock.ev.on("creds.update", saveCreds)

/* CONNECTION UPDATE */

sock.ev.on("connection.update", (update)=>{
console.log("FULL UPDATE:", update)

const {connection,qr,lastDisconnect} = update
console.log("EVENT:", connection)

if(qr){
console.log("QR généré 🔥", seller_id)

qrCodes[seller_id] = qr
clientStatus.set(seller_id,"qr_waiting") // 🔥 AJOUTE ÇA
updateBotStatus(seller_id,"qr_waiting")

if(qrTimers[seller_id]){
clearTimeout(qrTimers[seller_id])
}

qrTimers[seller_id] = setTimeout(()=>{

delete qrCodes[seller_id]

clientStatus.set(seller_id,"qr_expired")

console.log("QR expiré", seller_id)

},300000)

console.log("QR généré pour", seller_id)
}

if(connection === "connecting"){
    console.log("EVENT: connecting")
    clientStatus.set(seller_id,"handshake")
}

if(connection === "open"){

updateBotStatus(seller_id,"connected")

console.log("WhatsApp connecté", seller_id)

connectingSellers.delete(seller_id)
reconnectAttempts.delete(seller_id)

clientStatus.set(seller_id,"connected")

}

if(connection === "close"){

    const statusCode = lastDisconnect?.error?.output?.statusCode

    console.log("STATUS CODE:", statusCode)

    // 🔴 1. utilisateur a logout lui-même → STOP
    if(statusCode === DisconnectReason.loggedOut){
        console.log("🚫 Déconnecté volontairement", seller_id)

        try{
            fs.rmSync(`sessions/${seller_id}`, { recursive: true, force: true })
        }catch(e){}

        delete clients[seller_id]
        delete qrCodes[seller_id]
        connectingSellers.delete(seller_id)
        reconnectAttempts.delete(seller_id)
        clientStatus.set(seller_id, "disconnected")

        // 🔥 relancer pour générer un nouveau QR
        setTimeout(() => connectSeller(seller_id), 1000)
        return
    }

    // 🔴 2. session morte → supprimer + STOP
    if(statusCode === 401){
        console.log("SESSION INVALIDE", seller_id)

        try{
            fs.rmSync(`sessions/${seller_id}`, { recursive: true, force: true })
        }catch(e){}

        reconnectAttempts.delete(seller_id)
        clientStatus.set(seller_id,"disconnected")

        delete clients[seller_id]
        delete qrCodes[seller_id]

        setTimeout(() => connectSeller(seller_id), 1000)
        return
    }

    // 🔁 3. AUTRES CAS → retry automatique
    const retries = reconnectAttempts.get(seller_id) || 0

    if(retries < MAX_RETRIES){

        const delay = Math.min(2000 * (retries + 1), 15000)

        console.log(`🔄 Reconnexion dans ${delay}ms (${retries + 1}/${MAX_RETRIES})`)

        reconnectAttempts.set(seller_id, retries + 1)

        // nettoyage propre
        const client = clients[seller_id]
        if(client){
            try{
                client.end()
                client.ev.removeAllListeners()
            }catch(e){}
        }

        delete clients[seller_id]
        delete qrCodes[seller_id]
        connectingSellers.delete(seller_id)

        setTimeout(()=>{
            connectSeller(seller_id)
        }, delay)

    } else {

        console.log("❌ Max retries atteint", seller_id)

        reconnectAttempts.delete(seller_id)
        clientStatus.set(seller_id,"disconnected")

        delete clients[seller_id]
        delete qrCodes[seller_id]
    }
}

})

sock.ev.on("messages.upsert", async ({messages,type})=>{

const seller_id = sock.seller_id

if(type !== "notify") return

const msg = messages[0]

if(!msg.message) return

console.log("MESSAGE STRUCTURE:", JSON.stringify(msg.message, null, 2))

// 🔥 GESTION MESSAGE VOCAL
if(msg.message.audioMessage){
    console.log("🎤 Message vocal reçu")

    const client = clients[seller_id]

    if(client){

        let assistantName = "assistant"
        let sellerName = "ce vendeur"

        try{
            const res = await fetch(`http://localhost:8000/api/seller/${seller_id}`)
            const data = await res.json()

            if(data.assistant_name){
                assistantName = data.assistant_name
            }

            if(data.name){
                sellerName = data.name
            }

        }catch(e){
            console.log("Erreur récupération infos vendeur")
        }

        await client.sendMessage(msg.key.remoteJid, {
            text: `👋 Bonjour !

Je suis l’assistant de ${sellerName} 🤖

Je m’occupe de répondre rapidement aux messages.

🎤 Pour le moment je ne peux pas écouter les vocaux.

✍️ Merci d’écrire votre message, je vous réponds tout de suite 😊`
        })
    }

    return
}

// ignorer vieux messages
const msgTime = msg.messageTimestamp * 1000
const now = Date.now()

const originalJid = msg.key.remoteJid  // ← garder le JID complet

if(now - msgTime > 30000){
return
}

// const from = msg.key.remoteJid
let from = msg.key.remoteJid

// ❌ ignorer groupes
// ❌ ignorer groupes
if(from.endsWith("@g.us")) return

// 🔥 cas @lid → on garde le JID tel quel, pas de nettoyage
if(from.endsWith("@lid")){
    // on utilise directement le remoteJid pour l'envoi
    // pas de nettoyage, pas de return
    const text =
        msg.message.conversation ||
        msg.message.extendedTextMessage?.text ||
        msg.message.imageMessage?.caption

    if(!text || text.length > 500) return

    // pousser directement dans la queue avec le JID complet
    messageQueues[seller_id] = messageQueues[seller_id] || []
    messageQueues[seller_id].push({
        msg: {
            body: text,
            from: from,
            jid: originalJid,
            notifyName: msg.pushName
        }
    })
    processQueue(seller_id)
    return
}

// 🔥 nettoyer
if(from.includes("@")){
    from = from.split("@")[0]
}

// 🔥 filtrer
if(!from || from.length > 15){
    console.log("ID invalide ignoré:", from)
    return
}

const text =
msg.message.conversation ||
msg.message.extendedTextMessage?.text ||
msg.message.imageMessage?.caption

//if(!text) return

if(!from) return

if(!text || text.length > 500){
console.log("message trop long ignoré")
return
}

if(from.endsWith("@g.us")) return

console.log("MESSAGE RECU:", text)

sellerLastActivity.set(seller_id, Date.now())

const now2 = Date.now()
const key = seller_id + "_" + from

// anti spam message
if(lastMessageTime.get(key) && now2 - lastMessageTime.get(key) < 2000){
return
}

lastMessageTime.set(key, now2)

// création queue vendeur si nécessaire
if(!messageQueues[seller_id]){
messageQueues[seller_id] = []
}

// limite queue
if(messageQueues[seller_id].length > 50){
console.log("Queue overflow")
return
}

messageQueues[seller_id].push({
    msg: {
        body: text,
        from: from,           // pour identifier le client
        jid: originalJid,     // 🔥 pour envoyer le message
        notifyName: msg.pushName
    }
})

console.log("MESSAGE AJOUTE A LA QUEUE")

processQueue(seller_id)

})

}


async function updateBotStatus(seller_id, status){

try{

await fetch("http://localhost:8000/api/bot_status",{

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({
seller_id: seller_id,
status: status
})

})

}catch(e){

console.log("Erreur update bot status")

}

}

async function restoreSessions(){

    if(!fs.existsSync("./sessions")){
        fs.mkdirSync("./sessions")
        return
    }

    const sellers = fs.readdirSync("./sessions")

    for(const seller_id of sellers){

        console.log("♻️ Restauration session", seller_id)

        setTimeout(()=>{
            connectSeller(seller_id)
        }, Math.random() * 5000) // évite surcharge
    }
}

/*app.post("/connect", async (req,res)=>{

const seller_id = String(req.body.seller_id)

// 🔥 si déjà connecté → ok
if(clientStatus.get(seller_id) === "connected"){
    return res.json({message:"Déjà connecté"})
}

// 🔥 si QR expiré ou bloqué → reset
const status = clientStatus.get(seller_id)

if(
    status === "qr_waiting" && !qrCodes[seller_id] ||
    status === "qr_expired"
){
    console.log("Reset session", seller_id)

    const client = clients[seller_id]

    if(client){
        try{
            client.end()
            client.ev.removeAllListeners()
        }catch(e){}
    }

    delete clients[seller_id]
    delete qrCodes[seller_id]
    connectingSellers.delete(seller_id)
}

// 🔥 relancer connexion
await connectSeller(seller_id)

res.json({message:"Connexion lancée"})
})*/
app.post("/reset/:seller_id", async (req, res) => {

const seller_id = String(req.params.seller_id)

console.log("RESET FORCE", seller_id)

// 🔥 cleanup propre
await safeDisconnect(seller_id)

// 🔥 nettoyage total RAM
delete messageQueues[seller_id]
delete queueProcessing[seller_id]
reconnectAttempts.delete(seller_id)

clientStatus.set(seller_id,"disconnected")

// 🔥 supprimer session disque
fs.rmSync(`sessions/${seller_id}`, { recursive: true, force: true })

// 🔥 relancer
await connectSeller(seller_id)

res.json({ message: "reset + nouveau QR" })

})

/*app.post("/reset/:seller_id", async (req, res) => {

const seller_id = String(req.params.seller_id)

console.log("RESET FORCE", seller_id)

// 🔥 fermer proprement
const client = clients[seller_id]

if(client){
    try{
        client.end()
        client.ev.removeAllListeners()
    }catch(e){}
}

// 🔥 nettoyage total RAM
delete clients[seller_id]
delete qrCodes[seller_id]
delete messageQueues[seller_id]
delete queueProcessing[seller_id]

connectingSellers.delete(seller_id)
reconnectAttempts.delete(seller_id)

clientStatus.set(seller_id,"disconnected")

// 🔥 relancer direct
await safeDisconnect(seller_id)

fs.rmSync(`sessions/${seller_id}`, { recursive: true, force: true })

await connectSeller(seller_id)

res.json({ message: "reset + nouveau QR" })

})*/

app.get("/qr/:seller_id", async (req,res)=>{

const seller_id = String(req.params.seller_id)

const qr = qrCodes[seller_id]

const status = clientStatus.get(seller_id)

// 🔥 si expiré → forcer reconnect
if(status === "qr_expired"){

    console.log("Regen QR", seller_id)

    const client = clients[seller_id]

    if(client){
        try{
            client.end()
            client.ev.removeAllListeners()
        }catch(e){}
    }

    delete clients[seller_id]
    delete qrCodes[seller_id]
    connectingSellers.delete(seller_id)

    await safeDisconnect(seller_id)
    await connectSeller(seller_id)

    return res.json({status:"regenerating"})
}

if(!qr){
return res.json({status:"waiting"})
}

res.json({
status:"qr_ready",
qr:qr
})

})

app.get("/status/:seller_id",(req,res)=>{

const seller_id = String(req.params.seller_id)

const status = clientStatus.get(seller_id) || "disconnected"

res.json({status})

})

app.post("/disconnect/:seller_id",(req,res)=>{

const seller_id = String(req.params.seller_id)

const client = clients[seller_id]

if(client){

client.end()

delete clients[seller_id]
delete qrCodes[seller_id]
delete messageQueues[seller_id]
delete queueProcessing[seller_id]

sellerLastActivity.delete(seller_id)
connectingSellers.delete(seller_id)
reconnectAttempts.delete(seller_id)

clientStatus.set(seller_id,"disconnected")

}

res.json({message:"déconnecté"})

})

async function processQueue(seller_id){

if(!clients[seller_id]){

console.log("Session fermée, reconnexion", seller_id)

await connectSeller(seller_id)

await new Promise(resolve => setTimeout(resolve,6000))

if(!clients[seller_id]){
console.log("Impossible de reconnecter", seller_id)
return
}

}

if(queueProcessing[seller_id]) return

queueProcessing[seller_id] = true

const queue = messageQueues[seller_id]

while(queue && queue.length > 0){

await new Promise(resolve => setImmediate(resolve))

const item = queue.shift()

const { msg } = item

try{

const controller = new AbortController()

setTimeout(()=>controller.abort(),10000)

const rate = sellerRateLimit.get(seller_id) || {
count:0,
time:Date.now()
}

if(Date.now() - rate.time > 60 * 60 * 1000){
rate.count = 0
rate.time = Date.now()
}

rate.count++

if(rate.count > 60){
console.log("⛔ RATE LIMIT HORAIRE vendeur", seller_id)
continue
}

sellerRateLimit.set(seller_id, rate)

console.log("ENVOI A FASTAPI:", msg.body)

let response

try{

let subCheck

try{
    subCheck = await fetch(`http://localhost:8000/api/check_subscription/${seller_id}`)
    const subData = await subCheck.json()

    if(!subData.active){
        console.log("⛔ Abonnement expiré → blocage bot", seller_id)
        continue
    }

}catch(e){
    console.log("Erreur vérification abonnement")
    continue
}

// ✅ seulement si actif → on envoie à FastAPI
response = await fetch(
`http://localhost:8000/whatsapp/${seller_id}`,
{
method:"POST",
headers:{
"Content-Type":"application/json"
},
signal:controller.signal,
body:JSON.stringify({
Body:msg.body,
From:msg.from,
ProfileName:msg.notifyName || "Client"
})
}
)

}catch(err){

console.log("FASTAPI TIMEOUT")

continue

}

const text = await response.text()

if(!text || text.trim()===""){
continue
}

const client = clients[seller_id]

if(!client){
continue
}

const replyKey = seller_id + "_" + msg.from
const now = Date.now()

// anti spam reply
if(lastReplyTime.get(replyKey) && now - lastReplyTime.get(replyKey) < 5000){
continue
}

lastReplyTime.set(replyKey, now)

// const delay = Math.floor(Math.random()*5000)+5000
const textLength = msg.body.length

let baseDelay = 3000

if(textLength > 20) baseDelay += 3000
if(textLength > 50) baseDelay += 3000

const delay = baseDelay + Math.floor(Math.random() * 5000)

await new Promise(resolve => setTimeout(resolve,delay))

try {

    // 🔥 indiquer "en train d'écrire"
    await client.sendPresenceUpdate('composing', msg.jid)

    // 🔥 simuler le temps de frappe (proportionnel à la longueur de la réponse)
    const typingDelay = Math.min(text.length * 30, 4000)
    await new Promise(resolve => setTimeout(resolve, typingDelay))

    await client.sendPresenceUpdate('paused', msg.jid)

    await client.sendMessage(msg.jid, { text: text })

} catch(err) {
    console.log("SEND ERROR", err)
}

}catch(err){

console.log("message error",err)

}

}

queueProcessing[seller_id] = false

if(messageQueues[seller_id]?.length === 0){
delete messageQueues[seller_id]
}

}

const PORT = process.env.PORT || 10000;

if (!cluster.isPrimary) {

  app.get('/', (req, res) => {
    res.send('WhatsApp AI bot is running 🚀');
  });

  app.listen(PORT, async () => {
    console.log(`🔥 Worker ${cluster.worker.id} running on port ${PORT}`);

    if(cluster.worker.id === 1){
      await restoreSessions();
    }
  });

}
