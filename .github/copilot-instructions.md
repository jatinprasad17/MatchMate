## Project overview

MatchMate is a sports digest app. A user selects the sports/teams they
follow (football, cricket, F1 — chosen via dropdown, not free text),
and the app tracks upcoming fixtures for those teams and sends a weekly
digest, pushing events to the user's Google Calendar.

Stack (decided, do not suggest alternatives unless something is broken):
- Backend: FastAPI (Python)
- DB: Supabase (Postgres)
- Cache: Redis (planned, not built yet) — will cache fetched match data
  shared across users following the same team, TTL aligned to the
  weekly digest cycle
- Orchestration: LangGraph (planned, not built yet) — will handle
  fetching match data, personalizing per user, writing the digest,
  and delivering it
- Frontend: React via Vite (not started yet)
- Auth: Google OAuth for Calendar access (not built yet)
- LLM: bring-your-own-key model (Gemini), passed per-request, never
  stored server-side as a shared key

Current DB tables: users, follows (user_id, sport, team_or_player).
oauth_tokens and digest_runs tables are planned but not yet created.

Built and tested so far: health check, Supabase connection,
GET /users/{user_id}, POST /follows, GET /follows/{user_id},
GET /teams?sport=. An earlier free-text LLM extraction endpoint
(/extract-follows) was built then shelved — it couldn't reliably
resolve vague input (e.g. "city") to a specific real team, so we
switched to explicit dropdown selection as the primary flow instead.

Not yet built: locking /follows validation against the /teams list,
the React frontend, Redis caching, the LangGraph pipeline, Google OAuth,
and calendar/email delivery.

## Step-by-step build process

We build this project in small, sequential increments, not in one pass.
Follow this process for every request:

1. Before writing any code, restate in one or two sentences what you're
   about to build and why it's the logical next piece given the current
   state described above.

2. If anything about the request is ambiguous, or you'd have to make an
   assumption to proceed, ask a clarifying question BEFORE writing code.

3. Build ONLY the single feature/endpoint/piece asked for. Do not
   anticipate future needs or add anything beyond the current scope,
   even if it seems related or "obviously needed soon."

4. After the code is written, always tell me:
   - Exactly what to test with (sample inputs)
   - What the expected output/response should look like for each test
   - At least one edge case or invalid-input test, not just the happy path

5. Explicitly ask me to confirm the tests pass before suggesting what the
   next logical piece to build would be. Never assume the current piece
   works and move on automatically.

6. When suggesting what to build next, propose ONE next step, briefly
   explain why it's next given the project overview above, and wait for
   my confirmation before building it.

7. Whenever the project overview above becomes outdated (a new table,
   endpoint, or architectural decision), mention that the overview
   section should be updated, so it doesn't go stale as we build.