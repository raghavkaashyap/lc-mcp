// Run in your browser's developer console on https://leetcode.com while signed in.
// Downloads problem titles and solved statuses; never downloads cookies.
(async () => {
  const response = await fetch('/api/problems/all/', {credentials: 'same-origin'});
  if (!response.ok) throw new Error(`Catalog request failed: HTTP ${response.status}`);
  const data = await response.json();
  if (!data.user_name || !Array.isArray(data.stat_status_pairs)) {
    throw new Error('No signed-in catalog returned. Check that you are logged in.');
  }
  const url = URL.createObjectURL(new Blob([JSON.stringify(data)], {type:'application/json'}));
  const link = document.createElement('a');
  link.href = url; link.download = 'leetcode-catalog.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
})();
