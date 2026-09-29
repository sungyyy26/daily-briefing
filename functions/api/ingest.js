// POST {source: "meta"|"amazon", updatedAt, facts:[{date,line,form,...metrics}]}
// Auth: "Authorization: Bearer <INGEST_TOKEN>". Stores in KV binding SALES.
export async function onRequestPost({ request, env }) {
  if (request.headers.get("Authorization") !== `Bearer ${env.INGEST_TOKEN}`) return new Response("unauthorized", { status: 401 });
  const b = await request.json();
  if (!["meta", "amazon"].includes(b.source) || !Array.isArray(b.facts)) return new Response("bad request", { status: 400 });
  await env.SALES.put(b.source, JSON.stringify({ updatedAt: b.updatedAt || new Date().toISOString(), facts: b.facts }));
  return Response.json({ ok: true, stored: b.facts.length });
}
