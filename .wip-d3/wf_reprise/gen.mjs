import fs from 'fs'
import { writerPrompt, auditPairPrompt, base } from './prompts.mjs'
const [,, mode, argsFile, ...names] = process.argv
const all = JSON.parse(fs.readFileSync(argsFile)).quizzes
const pick = names.map(n => { const q = all.find(q => base(q) === n); if (!q) throw new Error('absent: ' + n); return q })
fs.mkdirSync('../prompts', { recursive: true })
if (mode === 'write') for (const q of pick) { const p = `../prompts/write_${base(q)}.md`; fs.writeFileSync(p, writerPrompt(q)); console.log(p) }
else { const p = `../prompts/audit_${pick.map(base).join('+')}.md`; fs.writeFileSync(p, auditPairPrompt(pick, pick.map(() => ({ notes: 'rédigé lors d\'un passage précédent' })))); console.log(p) }
