/**
 * Browser-side helper: fetch Wikipedia images and POST to local receiver.
 *
 * Usage (in browser console or via browser tool evaluate):
 *   1. Paste this script
 *   2. Call: await fetchAndSend(landmarks, 'http://localhost:8799')
 *
 * landmarks = { 'tower-of-london': 'Tower_of_London', 'gherkin': '30_St_Mary_Axe', ... }
 */

async function fetchWikiImage(wikiTitle) {
  const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(wikiTitle)}`;
  const resp = await fetch(url);
  const data = await resp.json();
  const thumb = data.thumbnail?.source?.replace(/\/\d+px-/, '/600px-');
  if (!thumb) return null;
  const imgResp = await fetch(thumb);
  const blob = await imgResp.blob();
  return new Promise(resolve => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]); // base64
    reader.readAsDataURL(blob);
  });
}

async function fetchAndSend(landmarks, serverUrl = 'http://localhost:8799') {
  const payload = {};
  for (const [name, title] of Object.entries(landmarks)) {
    try {
      const b64 = await fetchWikiImage(title);
      if (b64) {
        payload[name] = b64;
        console.log(`✅ ${name} (${(b64.length / 1024).toFixed(0)}KB b64)`);
      } else {
        console.log(`⚠️ ${name}: no image`);
      }
    } catch (e) {
      console.log(`❌ ${name}: ${e.message}`);
    }
  }
  const resp = await fetch(serverUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  console.log(`Sent ${Object.keys(payload).length} images → ${await resp.text()}`);
}
