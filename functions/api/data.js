// GET → {sync:{metaUpdatedAt, amazonUpdatedAt, currency, note}, facts:[merged by date/line/form]}
export async function onRequestGet({ env }) {
  const [meta, amz] = await Promise.all(["meta", "amazon"].map(k => env.SALES.get(k, "json")));
  const m = new Map();
  for (const src of [meta, amz]) for (const f of src?.facts || []) {
    const k = `${f.date}_${f.line}_${f.form}`;
    m.set(k, { ...(m.get(k) || {}), ...f });
  }
  return Response.json({
    sync: { metaUpdatedAt: meta?.updatedAt, amazonUpdatedAt: amz?.updatedAt, currency: "USD", note: amz?.facts?.length ? "" : "Amazon: waiting for AX sync" },
    facts: [...m.values()],
  }, { headers: { "Cache-Control": "no-store" } });
}
