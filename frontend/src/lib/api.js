const BASE = '/api'

function getToken() {
  return localStorage.getItem('rally_token')
}

function authHeaders() {
  const t = getToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

async function req(method, path, body, isForm = false) {
  const headers = { ...authHeaders() }
  if (body && !isForm) headers['Content-Type'] = 'application/json'

  const res = await fetch(BASE + path, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  })

  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `Fehler ${res.status}`)
  return data
}

// Auth
export const api = {
  register: (d)  => req('POST', '/auth/register', d),
  login:    (d)  => req('POST', '/auth/login', d),
  logout:   ()   => req('POST', '/auth/logout'),
  me:       ()   => req('GET',  '/auth/me'),

  // Rennen
  getRennen:        ()          => req('GET',    '/rennen'),
  getRennenById:    (id)        => req('GET',    `/rennen/${id}`),
  createRennen:     (d)         => req('POST',   '/rennen', d),
  updateRennen:     (id, d)     => req('PUT',    `/rennen/${id}`, d),
  deleteRennen:     (id)        => req('DELETE', `/rennen/${id}`),
  startenRennen:    (id)        => req('POST',   `/rennen/${id}/starten`),
  abschliessenRennen:(id)       => req('POST',   `/rennen/${id}/abschliessen`),
  resetRennen:      (id)        => req('POST',   `/rennen/${id}/reset`),
  zeitenLoeschen:   (id)        => req('DELETE', `/rennen/${id}/zeiten`),

  // Anmeldung
  anmelden:         (id, d)     => req('POST',   `/rennen/${id}/anmelden`, d),
  abmelden:         (id)        => req('DELETE', `/rennen/${id}/abmelden`),
  getTeilnehmer:    (id)        => req('GET',    `/rennen/${id}/teilnehmer`),
  getLeaderboard:   (id)        => req('GET',    `/rennen/${id}/leaderboard`),
  manuellAnmelden:  (id, d)     => req('POST',   `/rennen/${id}/anmelden-manuell`, d),
  csvImport:        (id, form)  => req('POST',   `/rennen/${id}/csv-import`, form, true),

  // Check-in
  checkin:          (rid, uid)  => req('POST',   `/rennen/${rid}/checkin/${uid}`),

  // Zeiten / Strafzeiten
  zeitEintragen:    (d)         => req('POST',   '/zeiten', d),
  strafzeitHinzufuegen:(d)      => req('POST',   '/strafzeiten', d),
  getStrafzeiten:   (rid, fid)  => req('GET',    `/strafzeiten/${rid}/${fid}`),
  strafzeitLoeschen:(id)        => req('DELETE', `/strafzeiten/${id}`),

  // Profil
  getAnmeldungen:   ()          => req('GET',    '/profil/anmeldungen'),
  getQrCode:        (uid)       => `${BASE}/fahrer/${uid}/qrcode`,

  // Kamera
  torSignal:        (d)         => req('POST',   '/kamera/tor', d),
  kameraConfig:     ()          => req('GET',    '/kamera/config'),
  laufReset:        (fid, rid)  => req('DELETE', `/kamera/lauf/${fid}/${rid}/reset`),

  // PDF & Urkunden
  ergebnissePdf:    (id)        => `${BASE}/rennen/${id}/ergebnisse/pdf`,
  urkunden:         (id)        => `${BASE}/rennen/${id}/urkunden`,

  // Ergebnis-Mail
  ergebnismail:     (id)        => req('POST',   `/rennen/${id}/ergebnismail`),

  // Demo
  demoErstellen:    (id)        => req('POST',   `/rennen/${id}/demo`),

  // Admin-Tools
  datenLoeschen:    ()          => req('POST',   '/admin/daten-loeschen'),
  backup:           ()          => `${BASE}/admin/backup?token=${getToken() || ''}`,

  // Info
  netzwerkInfo:     ()          => req('GET',    '/netzwerk-info'),
}
