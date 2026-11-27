import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

function moduleUrl(source) {
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
  })
  return `data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`
}

const authUrl = moduleUrl(await readFile(new URL('../src/auth.ts', import.meta.url), 'utf8'))
const chatSource = (await readFile(new URL('../src/chatApi.ts', import.meta.url), 'utf8')).replace("'./auth'", JSON.stringify(authUrl))
const { sendQuestion, questionText } = await import(moduleUrl(chatSource))
const userId = 'test-user'
const chatId = '12345678-1234-4234-8234-123456789abc'
const session = { user_id: userId, user_role: 'user' }
const answer = { chat_id: chatId, model: 'test-model', response: 'Ответ backend' }
const json = (payload, status = 200) => new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } })

for (const existingId of [undefined, chatId]) {
  test(`sends question to backend with cookies and chat_id=${existingId}`, async (t) => {
    const calls = []
    t.mock.method(globalThis, 'fetch', async (url, options) => {
      calls.push({ url, options })
      return url === '/api/v1/auth/me' ? json(session) : json(answer)
    })

    assert.deepEqual(await sendQuestion('  Вопрос  ', userId, existingId), answer)
    assert.equal(calls.length, 2)
    assert.equal(calls[1].url, '/api/v1/chat/promt' + (existingId ? `?chat_id=${existingId}` : ''))
    assert.equal(calls[1].options.method, 'POST')
    assert.equal(calls[1].options.credentials, 'same-origin')
    assert.equal(calls[1].options.headers['Content-Type'], 'application/json')
    assert.deepEqual(JSON.parse(calls[1].options.body), { message: 'Вопрос' })
  })
}

test('refreshes expired session before sending the question once', async (t) => {
  const urls = []
  const responses = [json({ detail: 'expired' }, 400), new Response(null, { status: 204 }), json(session), json(answer)]
  t.mock.method(globalThis, 'fetch', async (url) => { urls.push(url); return responses.shift() })

  assert.deepEqual(await sendQuestion('Вопрос', userId), answer)
  assert.deepEqual(urls, ['/api/v1/auth/me', '/api/v1/auth/refresh', '/api/v1/auth/me', '/api/v1/chat/promt'])
})

test('does not send the question under a changed account', async (t) => {
  const fetch = t.mock.method(globalThis, 'fetch', async () => json({ ...session, user_id: 'another-user' }))

  await assert.rejects(sendQuestion('Вопрос', userId), /аккаунт изменился/)
  assert.equal(fetch.mock.callCount(), 1)
})

test('does not send the question when session cannot be renewed', async (t) => {
  const urls = []
  t.mock.method(globalThis, 'fetch', async (url) => { urls.push(url); return json({ detail: 'expired' }, 401) })

  await assert.rejects(sendQuestion('Вопрос', userId), /Сессия завершилась/)
  assert.ok(urls.every((url) => url.startsWith('/api/v1/auth/')))
})

for (const status of [400, 401, 403, 404, 422, 429, 500]) {
  test(`HTTP ${status} is shown as an error without demo fallback or retry`, async (t) => {
    let posts = 0
    t.mock.method(globalThis, 'fetch', async (url) => {
      if (url === '/api/v1/auth/me') return json(session)
      posts += 1
      return json({ detail: 'provider error' }, status)
    })

    await assert.rejects(sendQuestion('Вопрос', userId))
    assert.equal(posts, 1)
  })
}

for (const payload of [null, {}, { ...answer, response: '' }, { ...answer, response: 42 }, { ...answer, chat_id: 'other-chat' }]) {
  test(`rejects malformed backend response ${JSON.stringify(payload)}`, async (t) => {
    t.mock.method(globalThis, 'fetch', async (url) => url === '/api/v1/auth/me' ? json(session) : json(payload))
    await assert.rejects(sendQuestion('Вопрос', userId, chatId), /некорректный ответ/)
  })
}

test('network failure never retries POST or synthesizes a successful answer', async (t) => {
  let posts = 0
  t.mock.method(globalThis, 'fetch', async (url) => {
    if (url === '/api/v1/auth/me') return json(session)
    posts += 1
    throw new TypeError('network failed')
  })

  await assert.rejects(sendQuestion('Вопрос', userId), /Не удалось получить ответ/)
  assert.equal(posts, 1)
})

test('includes the selected quote in the actual question', () => {
  const text = questionText('Почему?', { lecture: 'Алгебра', page: 2, text: 'Ax=0' })
  assert.equal(text, 'Почему?\n\nЦитата из «Алгебра», с. 2: Ax=0')
})

for (const message of ['', '   ', 'я'.repeat(101)]) {
  test(`invalid question is rejected before authorization and POST (${message.length} characters)`, async (t) => {
    const fetch = t.mock.method(globalThis, 'fetch', () => { throw new Error('Unexpected request') })
    await assert.rejects(sendQuestion(message, userId))
    assert.equal(fetch.mock.callCount(), 0)
  })
}

test('validates combined quote length and counts Unicode code points', () => {
  assert.throws(() => questionText('Вопрос', { lecture: 'Книга', page: 1, text: 'я'.repeat(100) }), /100 символов/)
  assert.equal(questionText('я'.repeat(100)).length, 100)
  assert.equal(Array.from(questionText('😀'.repeat(100))).length, 100)
})
