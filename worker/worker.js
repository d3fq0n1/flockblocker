/**
 * FlockBlocker Stories Worker
 * Handles submission, moderation, and display of "How has Flock hurt you?" stories.
 * Stores data in Cloudflare KV. Admin protected by ADMIN_PASSWORD env secret.
 */

const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
  "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
  "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
  "VA","WA","WV","WI","WY","DC"
];

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS },
  });
}

function htmlResponse(html, status = 200) {
  return new Response(html, {
    status,
    headers: { "Content-Type": "text/html;charset=UTF-8", ...CORS_HEADERS },
  });
}

async function hashIP(ip) {
  const data = new TextEncoder().encode(ip + "-flockblocker-salt");
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
}

function checkAuth(request, env) {
  const auth = request.headers.get("Authorization");
  if (!auth || !auth.startsWith("Basic ")) return false;
  const decoded = atob(auth.split(" ")[1]);
  const [user, pass] = decoded.split(":");
  return user === "admin" && pass === env.ADMIN_PASSWORD;
}

function requireAuth(env) {
  return new Response("Unauthorized", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="FlockBlocker Admin"', ...CORS_HEADERS },
  });
}

// --- Submission endpoint ---
async function handleSubmit(request, env) {
  if (request.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }

  let body;
  const contentType = request.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    body = await request.json();
  } else if (contentType.includes("form")) {
    const fd = await request.formData();
    body = Object.fromEntries(fd);
  } else {
    return jsonResponse({ error: "Unsupported content type" }, 400);
  }

  const { state, city, story, display_name, email } = body;

  // Validate
  if (!state || !US_STATES.includes(state)) {
    return jsonResponse({ error: "Invalid state" }, 400);
  }
  if (!city || typeof city !== "string" || city.trim().length === 0 || city.trim().length > 100) {
    return jsonResponse({ error: "City is required (max 100 chars)" }, 400);
  }
  if (!story || typeof story !== "string" || story.trim().length === 0 || story.trim().length > 1000) {
    return jsonResponse({ error: "Story is required (max 1000 chars)" }, 400);
  }
  if (display_name && typeof display_name === "string" && display_name.trim().length > 50) {
    return jsonResponse({ error: "Display name max 50 chars" }, 400);
  }
  if (email && typeof email === "string" && email.trim().length > 200) {
    return jsonResponse({ error: "Email max 200 chars" }, 400);
  }

  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const ipHash = await hashIP(ip);
  const id = crypto.randomUUID();
  const timestamp = new Date().toISOString();

  const submission = {
    id,
    state: state.trim(),
    city: city.trim(),
    story: story.trim(),
    display_name: display_name && display_name.trim() ? display_name.trim() : "Anonymous",
    email: email && email.trim() ? email.trim() : null,
    ip_hash: ipHash,
    timestamp,
    status: "pending", // pending | approved | rejected
  };

  // Store in KV: individual submission
  await env.SUBMISSIONS.put(`submission:${id}`, JSON.stringify(submission));

  // Add to pending index
  let pendingIndex = await env.SUBMISSIONS.get("index:pending", { type: "json" }) || [];
  pendingIndex.unshift(id);
  await env.SUBMISSIONS.put("index:pending", JSON.stringify(pendingIndex));

  return jsonResponse({ success: true, message: "Your story has been submitted for review. Thank you." });
}

// --- Public approved stories ---
async function handlePublicStories(env) {
  const approvedIndex = await env.SUBMISSIONS.get("index:approved", { type: "json" }) || [];
  const stories = [];

  for (const id of approvedIndex) {
    const data = await env.SUBMISSIONS.get(`submission:${id}`, { type: "json" });
    if (data && data.status === "approved") {
      stories.push({
        id: data.id,
        state: data.state,
        city: data.city,
        story: data.story,
        display_name: data.display_name,
        timestamp: data.timestamp,
      });
    }
  }

  // Sort by state, then city
  stories.sort((a, b) => a.state.localeCompare(b.state) || a.city.localeCompare(b.city));

  return jsonResponse(stories);
}

// --- Admin: list pending ---
async function handleAdminPending(request, env) {
  if (!checkAuth(request, env)) return requireAuth(env);

  const pendingIndex = await env.SUBMISSIONS.get("index:pending", { type: "json" }) || [];
  const submissions = [];

  for (const id of pendingIndex) {
    const data = await env.SUBMISSIONS.get(`submission:${id}`, { type: "json" });
    if (data && data.status === "pending") {
      submissions.push(data);
    }
  }

  return jsonResponse(submissions);
}

// --- Admin: moderate (approve/reject) ---
async function handleAdminModerate(request, env) {
  if (!checkAuth(request, env)) return requireAuth(env);
  if (request.method !== "POST") return jsonResponse({ error: "POST required" }, 405);

  const { id, action } = await request.json();
  if (!id || !["approve", "reject"].includes(action)) {
    return jsonResponse({ error: "Provide id and action (approve|reject)" }, 400);
  }

  const data = await env.SUBMISSIONS.get(`submission:${id}`, { type: "json" });
  if (!data) return jsonResponse({ error: "Submission not found" }, 404);

  data.status = action === "approve" ? "approved" : "rejected";
  await env.SUBMISSIONS.put(`submission:${id}`, JSON.stringify(data));

  // Remove from pending index
  let pendingIndex = await env.SUBMISSIONS.get("index:pending", { type: "json" }) || [];
  pendingIndex = pendingIndex.filter(i => i !== id);
  await env.SUBMISSIONS.put("index:pending", JSON.stringify(pendingIndex));

  // If approved, add to approved index
  if (action === "approve") {
    let approvedIndex = await env.SUBMISSIONS.get("index:approved", { type: "json" }) || [];
    approvedIndex.unshift(id);
    await env.SUBMISSIONS.put("index:approved", JSON.stringify(approvedIndex));
  }

  return jsonResponse({ success: true, id, status: data.status });
}

// --- Admin HTML page ---
function adminPageHTML() {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FlockBlocker Admin — Moderation Queue</title>
<style>
  :root { --bg:#09090b; --surface:#111116; --border:#242430; --accent:#c8f04a; --red:#f05a4a; --text:#d4d4dc; --text-mid:#8888a0; --text-dim:#44445a; --white:#f0f0f8; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:'Segoe UI',system-ui,sans-serif; padding:2rem; line-height:1.6; }
  h1 { color:var(--white); font-size:1.5rem; margin-bottom:0.5rem; }
  .subtitle { color:var(--text-dim); font-size:0.85rem; margin-bottom:2rem; }
  .card { background:var(--surface); border:1px solid var(--border); padding:1.5rem; margin-bottom:1rem; }
  .meta { font-size:0.75rem; color:var(--text-dim); margin-bottom:0.75rem; }
  .meta span { margin-right:1.5rem; }
  .story-text { color:var(--text); font-size:0.95rem; margin-bottom:1rem; white-space:pre-wrap; }
  .email { color:var(--text-dim); font-size:0.8rem; margin-bottom:1rem; }
  .actions { display:flex; gap:0.5rem; }
  .btn { padding:0.5rem 1.2rem; border:none; cursor:pointer; font-weight:600; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.05em; }
  .btn-approve { background:var(--accent); color:#09090b; }
  .btn-approve:hover { background:#d8ff5a; }
  .btn-reject { background:transparent; color:var(--red); border:1px solid var(--red); }
  .btn-reject:hover { background:var(--red); color:var(--white); }
  .empty { color:var(--text-dim); font-size:0.9rem; padding:3rem; text-align:center; }
  .status-msg { padding:0.5rem 1rem; margin-bottom:0.5rem; font-size:0.8rem; }
  .status-approved { color:var(--accent); }
  .status-rejected { color:var(--red); }
</style>
</head>
<body>
<h1>Moderation Queue</h1>
<p class="subtitle">Review and approve/reject story submissions</p>
<div id="queue"></div>
<script>
async function load() {
  const res = await fetch('/api/admin/pending');
  if (res.status === 401) { document.getElementById('queue').innerHTML = '<p class="empty">Authentication required. Reload and enter credentials.</p>'; return; }
  const items = await res.json();
  const el = document.getElementById('queue');
  if (!items.length) { el.innerHTML = '<p class="empty">No pending submissions.</p>'; return; }
  el.innerHTML = items.map(s => \`
    <div class="card" id="card-\${s.id}">
      <div class="meta">
        <span>\${s.state} — \${esc(s.city)}</span>
        <span>\${s.display_name}</span>
        <span>\${new Date(s.timestamp).toLocaleString()}</span>
        <span>IP: \${s.ip_hash}</span>
      </div>
      <div class="story-text">\${esc(s.story)}</div>
      \${s.email ? '<div class="email">Email: ' + esc(s.email) + '</div>' : ''}
      <div class="actions">
        <button class="btn btn-approve" onclick="moderate('\${s.id}','approve')">Approve</button>
        <button class="btn btn-reject" onclick="moderate('\${s.id}','reject')">Reject</button>
      </div>
    </div>
  \`).join('');
}
function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
async function moderate(id, action) {
  const res = await fetch('/api/admin/moderate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, action })
  });
  const data = await res.json();
  if (data.success) {
    const card = document.getElementById('card-' + id);
    card.innerHTML = '<p class="status-msg status-' + action + 'd">' + (action === 'approve' ? 'Approved' : 'Rejected') + '</p>';
  }
}
load();
</script>
</body>
</html>`;
}

// --- Router ---
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS_HEADERS });
    }

    if (path === "/api/submit" || path === "/api/submit/") {
      return handleSubmit(request, env);
    }
    if (path === "/api/stories" || path === "/api/stories/") {
      return handlePublicStories(env);
    }
    if (path === "/api/admin/pending" || path === "/api/admin/pending/") {
      return handleAdminPending(request, env);
    }
    if (path === "/api/admin/moderate" || path === "/api/admin/moderate/") {
      return handleAdminModerate(request, env);
    }
    if (path === "/admin" || path === "/admin/") {
      if (!checkAuth(request, env)) return requireAuth(env);
      return htmlResponse(adminPageHTML());
    }

    return jsonResponse({ error: "Not found" }, 404);
  },
};
