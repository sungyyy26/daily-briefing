// POST {system, messages:[{role, content}]} → {text}. Uses ANTHROPIC_API_KEY.
export async function onRequestPost({ request, env }) {
  const { system, messages } = await request.json();
  const r = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "x-api-key": env.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json" },
    body: JSON.stringify({ model: env.CLAUDE_MODEL || "claude-sonnet-5-5", max_tokens: 1200, system, messages: messages.slice(-12) }),
  });
  const j = await r.json();
  if (!r.ok) return Response.json({ error: j.error?.message || "AI request failed" }, { status: 502 });
  return Response.json({ text: j.content.filter(c => c.type === "text").map(c => c.text).join("") });
}
