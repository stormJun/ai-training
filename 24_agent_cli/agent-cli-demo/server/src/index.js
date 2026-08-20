import { createDemoServer } from './server.js'

const port = Number(process.env.PORT || 8787)
const server = createDemoServer()

await server.listen(port)
console.log(`agent-cli-demo server listening on ${server.baseUrl()}`)
