// 코드 검사: 문법, 단추가 부르는 기능이 실제로 있는지, 판 번호가 파일마다 같은지.
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const fail = [];
const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
const html = read('index.html');

const i = html.indexOf('<script>\n'), j = html.lastIndexOf('</script>');
const js = html.slice(i + 9, j);
const tmp = join(mkdtempSync(join(tmpdir(), 'zzim-')), 'app.js');
writeFileSync(tmp, js);
try { execFileSync(process.execPath, ['--check', tmp], { stdio: 'pipe' }); }
catch (e) { fail.push(`문법 오류: index.html 스크립트\n${e.stderr}`); }

const cases = new Set([...js.matchAll(/case '([\w-]+)':/g)].map((m) => m[1]));
cases.add('close-bg');
const acts = new Set();
for (const m of js.matchAll(/data-act="([\w-]+)"/g)) acts.add(m[1]);
for (const m of js.matchAll(/data-act="\$\{[^}]*\?'([\w-]+)':'([\w-]+)'\}"/g)) { acts.add(m[1]); acts.add(m[2]); }
for (const m of js.matchAll(/data-act="\$\{DEMO\?`<button data-act="([\w-]+)"/g)) acts.add(m[1]);
for (const a of acts) if (!cases.has(a)) fail.push(`단추가 부르는 기능이 없음: ${a}`);
for (const m of js.matchAll(/A\.(\w+)\(/g)) if (!new RegExp(`^\\s{2}${m[1]}\\(s,`, 'm').test(js)) fail.push(`없는 동작을 부름: A.${m[1]}`);

const version = (js.match(/const VERSION = '([\d.]+)'/) || [])[1];
if (!version) fail.push('판 번호(VERSION)가 없음');
const rv = (read('README.md').match(/판 ([\d.]+)/) || [])[1];
if (rv && rv !== version) fail.push(`README 판 번호 ${rv} ≠ ${version}`);

if (fail.length) { console.error(fail.join('\n')); process.exit(1); }
console.log(`코드 검사 통과 (v${version}, 단추 기능 ${acts.size}개)`);
