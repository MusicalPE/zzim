# 전체 시험 2: 가짜 파이어베이스로 구글 로그인·등록·내보내기 흐름을 밟아 봄
import asyncio, os, pathlib
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parent.parent
CHROME=os.environ.get('CHROME','/usr/bin/google-chrome')

fails=[]
def ok(c,m):
    print(('PASS ' if c else 'FAIL ')+m); 
    if not c: fails.append(m)
STUB=open(ROOT/'tests'/'fbstub.js').read()
FB=ROOT/'index.html'  # 파이어베이스 주소는 가짜(fbstub.js)로 바꿔 끼워서 진짜 서버에는 닿지 않음
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1100,'height':900})
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        async def route(r):
            body = STUB if 'firebase-app-compat' in r.request.url else '/*empty*/'
            await r.fulfill(status=200, content_type='application/javascript', body=body)
        await pg.route('**/www.gstatic.com/**', route)
        await pg.goto(FB.as_uri()+'?test=1'); await pg.wait_for_timeout(500)
        ok('구글 계정으로 로그인' in await pg.inner_text('#app'),'처음: 구글 로그인 단추')
        async def signin(uid,name,email):
            await pg.evaluate(f"window.__fakeUser={{uid:'{uid}',displayName:'{name}',email:'{email}'}}")
            await pg.click('[data-act=google]'); await pg.wait_for_timeout(300)
        await signin('uA','김체육','pe@x.com')
        ok('학교 코드' in await pg.inner_text('#app'),'로그인 뒤 학교 코드 화면')
        await pg.fill('#in-code','nope1234'); await pg.click('[data-act=code-go]'); await pg.wait_for_timeout(200)
        ok('없어요' in await pg.inner_text('#err'),'없는 학교 코드 안내')
        await pg.click('[data-act=new-school]')
        ok(await pg.input_value('#ns-me')=='김체육','내 이름 자동 채움')
        await pg.fill('#ns-code','haetsal1'); await pg.fill('#ns-name','햇살초등학교'); await pg.click('[data-act=ns-go]'); await pg.wait_for_timeout(400)
        ok(await pg.locator('table.grid').count()==1,'학교 만들고 바로 예약판')
        ok(await pg.locator('[data-act=view][data-v=settings]').count()==1,'만든 사람은 설정 보임')
        # 체육 시간표 하나 넣기 (학급 목록 필요)
        await pg.click('[data-act=view][data-v=settings]')
        await pg.fill('#set-classes','4-1, 4-2'); await pg.click('[data-act=save-school]'); await pg.wait_for_timeout(200)
        await pg.select_option('[data-tt="p_hall|1|1"]','4-1'); await pg.wait_for_timeout(200)
        # 나가기 → 담임 B 로그인
        await pg.click('[data-act=signout]'); await pg.wait_for_timeout(300)
        ok('구글 계정으로 로그인' in await pg.inner_text('#app'),'나가기 하면 구글 로그아웃')
        await signin('uB','이담임','b@x.com'); await pg.wait_for_timeout(300)
        txt=await pg.inner_text('#app')
        ok('처음 오셨네요' in txt,'지난 학교 코드 기억 → 바로 등록 화면')
        ok(await pg.input_value('#rg-name')=='이담임','이름 자동 채움')
        await pg.click('[data-act=rg-go]'); await pg.wait_for_timeout(100)
        ok('학년과 반' in await pg.inner_text('#err'),'담임은 학년·반 필수')
        await pg.select_option('#rg-grade','5'); await pg.fill('#rg-ban','2'); await pg.click('[data-act=rg-go]'); await pg.wait_for_timeout(300)
        ok(await pg.locator('table.grid').count()==1,'등록 후 예약판')
        ok('5-2' in await pg.inner_text('header'),'반 5-2 표시')
        ok(await pg.locator('[data-act=view][data-v=settings]').count()==0,'담임은 설정 안 보임')
        cls=await pg.evaluate("window.__jjim.S.school.classes")
        ok('5-2' in cls,'학급 목록에 5-2 자동 추가: '+str(cls))
        # 다시 로그인하면 등록 없이 바로
        await pg.click('[data-act=signout]'); await pg.wait_for_timeout(200); await signin('uB','이담임','b@x.com'); await pg.wait_for_timeout(300)
        ok(await pg.locator('table.grid').count()==1,'같은 계정은 바로 들어옴')
        # 신청 흐름 (학교판 저장)
        k=await pg.evaluate("(()=>{const d=new Date();d.setDate(d.getDate()+10);while(d.getDay()==0||d.getDay()==6)d.setDate(d.getDate()+1);const p=n=>String(n).padStart(2,'0');return 'p_hall|'+d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())+'|6'})()")
        r=await pg.evaluate(f"window.__jjim.store().update(s=>window.__jjim.A.bid(s,s.teachers.find(t=>t.id==='uB'),'{k}'))")
        ok(r.get('ok'),'학교판 신청 저장')
        # 같은 반 담임 중복 등록 막기 / 낯선 사람
        await pg.click('[data-act=signout]'); await pg.wait_for_timeout(200); await signin('uC','낯선이','c@x.com'); await pg.wait_for_timeout(300)
        await pg.select_option('#rg-grade','5'); await pg.fill('#rg-ban','2'); await pg.click('[data-act=rg-go]'); await pg.wait_for_timeout(200)
        ok('이미 등록' in await pg.inner_text('#err'),'같은 반 담임 중복 막힘')
        await pg.select_option('#rg-kind','other'); await pg.select_option('#rg-grade',''); await pg.fill('#rg-ban',''); await pg.click('[data-act=rg-go]'); await pg.wait_for_timeout(300)
        ok(await pg.locator('table.grid').count()==1,'교과 선생님은 학년·반 없이 등록')
        # 체육 선생님이 내보내기
        await pg.click('[data-act=signout]'); await pg.wait_for_timeout(200); await signin('uA','김체육','pe@x.com'); await pg.wait_for_timeout(300)
        await pg.click('[data-act=view][data-v=settings]')
        ok('c@x.com' in await pg.inner_text('main'),'설정에 메일 주소 보임')
        await pg.click('[data-act=t-del][data-id=uC]'); await pg.click('[data-act=t-del][data-id=uC]'); await pg.wait_for_timeout(300)
        ok(await pg.evaluate("!window.__jjim.S.teachers.some(t=>t.id==='uC')"),'체육 선생님이 내보내기')
        # 내보낸 사람이 다시 오면 등록 화면
        await pg.click('[data-act=signout]'); await pg.wait_for_timeout(200); await signin('uC','낯선이','c@x.com'); await pg.wait_for_timeout(300)
        ok('처음 오셨네요' in await pg.inner_text('#app'),'내보낸 계정은 다시 등록 화면')
        # 체육(관리자 아님) 선생님도 내보내기 가능, 관리자는 못 내보냄
        await pg.select_option('#rg-kind','pe'); await pg.fill('#rg-name','박체육'); await pg.click('[data-act=rg-go]'); await pg.wait_for_timeout(300)
        r=await pg.evaluate("window.__jjim.store().update(s=>{const me=s.teachers.find(t=>t.id==='uC'); /* 관리자 내보내기 시도 */ return null;})")
        await pg.click('[data-act=view][data-v=settings]')
        ok(await pg.locator('[data-act=t-del][data-id=uA]').count()==0,'관리자 아닌 체육 선생님에게는 관리자 내보내기 단추 없음')
        ok(await pg.locator('[data-act=t-del][data-id=uB]').count()==1,'관리자 아닌 체육 선생님도 담임 내보내기 가능')
        ok(not errs,'페이지 오류 없음 '+str(errs[:3]))
        await b.close()
    print('FAILS',len(fails))
    if fails: raise SystemExit(1)
asyncio.run(main())
