const express = require("express")
const bodyParser = require("body-parser")
const twilio = require("twilio")

const app = express()

app.use(bodyParser.urlencoded({ extended: false }))

app.post("/whatsapp", (req, res) => {

    const message = req.body.Body
    const from = req.body.From

    console.log("Message reçu:", message)

    const MessagingResponse = twilio.twiml.MessagingResponse
    const twiml = new MessagingResponse()

    twiml.message("Bonjour 👋 votre message a été reçu")

    res.writeHead(200, { "Content-Type": "text/xml" })
    res.end(twiml.toString())

})

app.listen(3000, () => {
    console.log("Serveur lancé sur port 3000")
})