import { useEffect, useState } from 'react'

export default function App() {
  const [customers, setCustomers] = useState([])
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')

  const load = () =>
    fetch('/api/customers')
      .then(r => r.json())
      .then(setCustomers)
      .catch(e => setError(String(e)))

  useEffect(() => { load() }, [])

  const add = async e => {
    e.preventDefault()
    const r = await fetch('/api/customers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email })
    })
    if (!r.ok) { setError('Save failed: ' + r.status); return }
    setName(''); setEmail(''); setError('')
    load()
  }

  return (
    <div style={{ fontFamily: 'sans-serif', maxWidth: 640, margin: '2rem auto' }}>
      <h1>Home Lab Customers</h1>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      <form onSubmit={add} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input placeholder="Name" value={name} onChange={e => setName(e.target.value)} required />
        <input placeholder="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
        <button type="submit">Add</button>
      </form>
      <table border="1" cellPadding="6" style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Created</th></tr></thead>
        <tbody>
          {customers.map(c => (
            <tr key={c.id}>
              <td>{c.id}</td><td>{c.name}</td><td>{c.email}</td>
              <td>{c.createdAt ? new Date(c.createdAt).toLocaleString() : ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
