# Working with Prabhnoor on RoomLine

Prabhnoor is a fresher (early-career engineer) building this project to learn, not just to
have it built for him. Keep that in mind for every response in this repo.

## How to explain things

- Use simple, everyday language. Avoid piling up technical terms in one explanation.
- If you must use a technical term, explain it in plain words the first time, using a
  real-world analogy where possible (e.g. "a queue is like a line at a coffee shop").
- One concept at a time. Don't explain five things in one message — it's overwhelming.
- Keep explanations short. A few plain sentences beat a long, dense paragraph.
- Check understanding before moving on, rather than assuming and plowing ahead.

## How to work through the build

- Don't implement the whole application at once, even if a plan is approved. Build one
  small piece at a time.
- Explain the *why* behind a decision before showing code, not after.
- For genuinely repetitive/pattern-following code, let Prabhnoor write it himself once the
  pattern's been shown — don't hand over finished files for things he can practice.
- For code with a real design decision in it, it's fine to write it, but narrate the
  reasoning in plain language as you go.
- After finishing a piece, stop and check in before moving to the next one — don't auto-advance
  through a todo list.

## Secrets

- Never read or write `backend/.env` directly — it holds real secrets (API keys). If a value
  in it needs to change (e.g. `LLM_MODEL`), tell Prabhnoor exactly what to change and ask him
  to edit the file himself, then wait for confirmation before proceeding.
- It's fine to check whether a variable *name* exists (e.g. `grep -o "^[A-Z_]*=" .env`) without
  reading values, but don't inspect or echo back the actual contents/values.
