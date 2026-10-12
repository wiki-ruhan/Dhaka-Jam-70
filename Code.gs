/**
 * Dhaka traffic study — Google Drive receiver (v6)
 * script.google.com এ পুরো কোড পেস্ট করুন, TOKEN-এ আগের গোপন শব্দই রাখুন,
 * তারপর Deploy → Manage deployments → ✏️ → Version: New version → Deploy (URL একই থাকে)।
 *
 * Drive-এ ফোল্ডার যেভাবে তৈরি হয়:
 *   Dhaka Traffic Snapshots/
 *     Screenshots/2026-10-13/   ← প্রতিদিনের সব ছবি (.webp) ও তথ্য (.json), ৩০ দিনে ৩০টি ফোল্ডার
 *     CSV/daily/                ← 2026-10-13_junctions.csv: প্রতি স্লটে ৭০টি মোড়ের মান (প্রতিদিন একটি ফাইল)
 *     CSV/legs/                 ← 2026-10-13_legs.csv: প্রতিটি মোড়ের প্রতিটি দিকের রাস্তা আলাদা
 *     CSV/ranking/              ← 2026-10-13_ranking.csv: সেদিনের সবচেয়ে খারাপ মোড়ের র‍্যাংকিং
 *     CSV/ranking_overall.csv   ← পুরো সময়ের র‍্যাংকিং
 *     data/                     ← snapshots.csv, thana.csv, conditions.csv, daily_summary.csv, junctions_exact.csv
 *
 * Actions:
 *   {action:"token"}                 → short-lived Drive access token (large images go straight to the Drive API)
 *   {action:"folder", path:[...]}    → id of My Drive/<path...>, created if missing
 *   {filename, data, mime, ...}      → save a small file (base64). Folder: path:[...]  or  subfolder + date
 */
const TOKEN = 'এখানে-আগের-গোপন-শব্দটাই-দিন';   // GitHub-এর DRIVE_TOKEN secret-এর সাথে হুবহু এক
const ROOT_FOLDER = 'Dhaka Traffic Snapshots';

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    if (body.token !== TOKEN) return reply_({ ok: false, error: 'wrong token' });

    if (body.action === 'token') {
      DriveApp.getRootFolder();                       // keeps the Drive permission active
      return reply_({ ok: true, access_token: ScriptApp.getOAuthToken() });
    }
    if (body.action === 'folder') {
      return reply_({ ok: true, id: path_(body.path || [ROOT_FOLDER]).getId() });
    }

    // small file (CSV): replace the older copy when overwrite = true
    let target;
    if (body.path && body.path.length) {
      target = path_([ROOT_FOLDER].concat(body.path));
    } else {
      const parts = [ROOT_FOLDER];
      if (body.subfolder) parts.push(body.subfolder);
      if (body.date) parts.push(body.date);
      target = path_(parts);
    }
    const bytes = Utilities.base64Decode(body.data);
    const existing = target.getFilesByName(body.filename);
    if (existing.hasNext()) {
      if (!body.overwrite) return reply_({ ok: true, skipped: true });
      existing.next().setTrashed(true);
    }
    const file = target.createFile(Utilities.newBlob(bytes, body.mime, body.filename));
    return reply_({ ok: true, id: file.getId() });
  } catch (err) {
    return reply_({ ok: false, error: String(err) });
  }
}

function doGet() {
  return reply_({ ok: true, message: 'Dhaka traffic Drive receiver v6 is running' });
}

// My Drive/<names...>, creating folders that do not exist yet
function path_(names) {
  let f = DriveApp.getRootFolder();
  names.forEach(function (name) { f = folder_(f, name); });
  return f;
}

function folder_(parent, name) {
  const it = parent.getFoldersByName(name);
  return it.hasNext() ? it.next() : parent.createFolder(name);
}

function reply_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
