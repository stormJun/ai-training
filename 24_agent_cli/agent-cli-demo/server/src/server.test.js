import test from 'node:test'
import assert from 'node:assert/strict'

import { createDemoServer } from './server.js'

async function postJson(baseUrl, path, body) {
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json'
    },
    body: JSON.stringify(body)
  })

  return {
    status: response.status,
    body: await response.json()
  }
}

async function getJson(baseUrl, path, token) {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: token
      ? {
          authorization: `Bearer ${token}`
        }
      : {}
  })

  return {
    status: response.status,
    body: await response.json()
  }
}

test('device auth flow issues token only after approval and unlocks dashboard summary', async () => {
  const server = createDemoServer()
  await server.listen(0)
  const baseUrl = server.baseUrl()

  try {
    const deviceCodeResult = await postJson(baseUrl, '/sso/device/code', {
      client_id: 'mp-sso-cli'
    })

    assert.equal(deviceCodeResult.status, 200)
    assert.equal(typeof deviceCodeResult.body.device_code, 'string')
    assert.equal(typeof deviceCodeResult.body.user_code, 'string')
    assert.match(deviceCodeResult.body.verification_uri, /\/mock\/approve\?user_code=/)

    const pendingTokenResult = await postJson(baseUrl, '/sso/device/token', {
      client_id: 'mp-sso-cli',
      device_code: deviceCodeResult.body.device_code
    })
    assert.equal(pendingTokenResult.status, 428)
    assert.equal(pendingTokenResult.body.error, 'authorization_pending')

    const approveResult = await postJson(baseUrl, '/sso/mock/approve', {
      user_code: deviceCodeResult.body.user_code
    })
    assert.equal(approveResult.status, 200)
    assert.equal(approveResult.body.status, 'approved')

    const tokenResult = await postJson(baseUrl, '/sso/device/token', {
      client_id: 'mp-sso-cli',
      device_code: deviceCodeResult.body.device_code
    })
    assert.equal(tokenResult.status, 200)
    assert.equal(typeof tokenResult.body.access_token, 'string')
    assert.equal(tokenResult.body.user.id, 'demo-user')

    const unauthorizedSummary = await getJson(baseUrl, '/api/dashboard/summary')
    assert.equal(unauthorizedSummary.status, 401)
    assert.equal(unauthorizedSummary.body.error, 'AUTH_REQUIRED')

    const authorizedSummary = await getJson(
      baseUrl,
      '/api/dashboard/summary',
      tokenResult.body.access_token
    )
    assert.equal(authorizedSummary.status, 200)
    assert.deepEqual(authorizedSummary.body.summary, {
      pending_reviews: 3,
      published_items: 12,
      today_visits: 248
    })
  } finally {
    await server.close()
  }
})

test('device code cannot be exchanged twice', async () => {
  const server = createDemoServer()
  await server.listen(0)
  const baseUrl = server.baseUrl()

  try {
    const deviceCodeResult = await postJson(baseUrl, '/sso/device/code', {
      client_id: 'mp-sso-cli'
    })

    await postJson(baseUrl, '/sso/mock/approve', {
      user_code: deviceCodeResult.body.user_code
    })

    const firstTokenResult = await postJson(baseUrl, '/sso/device/token', {
      client_id: 'mp-sso-cli',
      device_code: deviceCodeResult.body.device_code
    })
    assert.equal(firstTokenResult.status, 200)

    const secondTokenResult = await postJson(baseUrl, '/sso/device/token', {
      client_id: 'mp-sso-cli',
      device_code: deviceCodeResult.body.device_code
    })
    assert.equal(secondTokenResult.status, 410)
    assert.equal(secondTokenResult.body.error, 'expired_token')
  } finally {
    await server.close()
  }
})
