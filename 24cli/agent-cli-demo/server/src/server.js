import http from 'node:http'
import { randomUUID } from 'node:crypto'

const DEMO_USER = {
  id: 'demo-user',
  name: 'Demo User'
}

const DASHBOARD_SUMMARY = {
  pending_reviews: 3,
  published_items: 12,
  today_visits: 248
}

function json(response, statusCode, body) {
  response.writeHead(statusCode, {
    'content-type': 'application/json; charset=utf-8'
  })
  response.end(JSON.stringify(body))
}

async function readJson(request) {
  const chunks = []
  for await (const chunk of request) {
    chunks.push(chunk)
  }

  if (chunks.length === 0) {
    return {}
  }

  return JSON.parse(Buffer.concat(chunks).toString('utf8'))
}

function randomCode(prefix) {
  return `${prefix}_${randomUUID().replaceAll('-', '')}`
}

export function createDemoServer() {
  const deviceCodes = new Map()
  const accessTokens = new Map()
  let currentBaseUrl = 'http://127.0.0.1:0'

  const server = http.createServer(async (request, response) => {
    const url = new URL(request.url || '/', currentBaseUrl)

    if (request.method === 'POST' && url.pathname === '/sso/device/code') {
      const body = await readJson(request)
      if (!body.client_id) {
        return json(response, 400, {
          error: 'invalid_request',
          message: 'client_id is required'
        })
      }

      const record = {
        clientId: body.client_id,
        deviceCode: randomCode('dev'),
        userCode: randomCode('user').slice(0, 13).toUpperCase(),
        approved: false,
        consumed: false
      }
      deviceCodes.set(record.deviceCode, record)

      return json(response, 200, {
        device_code: record.deviceCode,
        user_code: record.userCode,
        verification_uri: `${currentBaseUrl}/mock/approve?user_code=${record.userCode}`,
        expires_in: 600,
        interval: 1
      })
    }

    if (request.method === 'POST' && url.pathname === '/sso/mock/approve') {
      const body = await readJson(request)
      const record = [...deviceCodes.values()].find((item) => item.userCode === body.user_code)
      if (!record) {
        return json(response, 404, {
          error: 'not_found',
          message: 'user_code not found'
        })
      }

      record.approved = true
      return json(response, 200, {
        status: 'approved',
        user: DEMO_USER
      })
    }

    if (request.method === 'POST' && url.pathname === '/sso/device/token') {
      const body = await readJson(request)
      const record = deviceCodes.get(body.device_code)
      if (!record || record.clientId !== body.client_id) {
        return json(response, 404, {
          error: 'invalid_device_code',
          message: 'device code not found'
        })
      }

      if (record.consumed) {
        return json(response, 410, {
          error: 'expired_token',
          message: 'device code already consumed'
        })
      }

      if (!record.approved) {
        return json(response, 428, {
          error: 'authorization_pending',
          message: 'waiting for approval'
        })
      }

      record.consumed = true
      const accessToken = randomCode('token')
      const expiresAt = new Date(Date.now() + 60 * 60 * 1000).toISOString()
      accessTokens.set(accessToken, {
        user: DEMO_USER,
        expiresAt
      })

      return json(response, 200, {
        access_token: accessToken,
        token_type: 'Bearer',
        expires_in: 3600,
        expires_at: expiresAt,
        user: DEMO_USER
      })
    }

    if (request.method === 'GET' && url.pathname === '/api/dashboard/summary') {
      const authHeader = request.headers.authorization || ''
      const token = authHeader.replace(/^Bearer\s+/i, '')
      const tokenRecord = accessTokens.get(token)

      if (!token || !tokenRecord) {
        return json(response, 401, {
          error: 'AUTH_REQUIRED',
          message: 'please run mp-sso-cli login'
        })
      }

      return json(response, 200, {
        summary: DASHBOARD_SUMMARY,
        user: tokenRecord.user
      })
    }

    if (request.method === 'GET' && url.pathname === '/mock/approve') {
      const userCode = url.searchParams.get('user_code') || ''
      const record = [...deviceCodes.values()].find((item) => item.userCode === userCode)
      if (record) {
        record.approved = true
      }

      response.writeHead(record ? 200 : 404, {
        'content-type': 'text/html; charset=utf-8'
      })
      response.end(
        record
          ? `<html><body><h1>Approved</h1><p>User code ${userCode} approved.</p></body></html>`
          : '<html><body><h1>Not Found</h1></body></html>'
      )
      return
    }

    json(response, 404, {
      error: 'not_found',
      message: 'route not found'
    })
  })

  return {
    async listen(port = 8787) {
      await new Promise((resolve) => {
        server.listen(port, '127.0.0.1', resolve)
      })
      const address = server.address()
      currentBaseUrl = `http://127.0.0.1:${address.port}`
    },
    async close() {
      if (!server.listening) {
        return
      }
      await new Promise((resolve, reject) => {
        server.close((error) => {
          if (error) {
            reject(error)
            return
          }
          resolve()
        })
      })
    },
    baseUrl() {
      return currentBaseUrl
    }
  }
}
