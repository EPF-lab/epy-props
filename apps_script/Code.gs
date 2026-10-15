// Apps Script: expone las hojas del libro Cruce_props_EPY_v1 como JSON para la página.
// Hojas esperadas: Jugadores (col R = ID de foto, opcional), Equipos, DvP.
function doGet() {
  const ss = SpreadsheetApp.getActive();
  const rows = n => ss.getSheetByName(n).getDataRange().getValues().slice(1);
  // [nombre, equipo25-26, equipo26-27, pos, posAlt, min, pts_base, reb_base, ast_base, posManual(1/0), idFoto]
  const players = rows('Jugadores').filter(r => r[0])
    .map(r => [r[0], r[1], r[2], r[4], r[5], r[7], r[14], r[15], r[16], r[6] === 'manual' ? 1 : 0, r[17] || '']);
  const teams = {}; rows('Equipos').forEach(r => teams[r[0]] = [r[2], r[1]]);      // nombre -> [continuidad, abrev]
  const dvp = {};                                                                  // equipo -> pos -> [pts, ast, reb, 3pm, stl]
  rows('DvP').forEach(r => { (dvp[r[0]] = dvp[r[0]] || {})[r[1]] = [r[2], r[3], r[4], r[5], r[6]]; });
  let updated = new Date().toISOString();                       // momento de la última edición del libro (indicador 'hace X h')
  try { updated = DriveApp.getFileById(ss.getId()).getLastUpdated().toISOString(); } catch (e) {}
  const out = { asof: new Date().toISOString().slice(0, 10), updated, players, teams, dvp };
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}
