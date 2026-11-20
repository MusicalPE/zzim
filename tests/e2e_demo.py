# 전체 시험 1: 체험 모드로 신청·마감·추첨·우천·설정 흐름을 밟아 봄
import asyncio, os, pathlib
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parent.parent
CHROME=os.environ.get('CHROME','/usr/bin/google-chrome')
URL=(ROOT/'index.html').as_uri()+'?test=1&demo'
fails=[]
def ok(c,m):
    print(('PASS ' if c else 'FAIL ')+m)
    if not c: fails.append(m)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1200,'height':900})
        errs=[]
        pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None)
        await pg.goto(URL); await pg.wait_for_timeout(300)
        # 수요일 오전으로 시간 고정 후 체험 기록 초기화
        await pg.evaluate("window.__jjim.setNow('2026-11-25T10:00:00')")
        await pg.evaluate("localStorage.clear()"); await pg.reload(); await pg.wait_for_timeout(300)
        await pg.evaluate("window.__jjim.setNow('2026-11-25T10:00:00')")
        async def login(name):
            if await pg.locator('[data-act=logout]').count(): await pg.click('[data-act=logout]')
            await pg.click(f'.tlist button:has-text("{name}")'); await pg.wait_for_timeout(100)
            await pg.click('[data-act=week][data-d="0"]')
        async def gotoWeek(mon):
            await pg.evaluate(f"(()=>{{}})()")
        await login('김체육')
        ok(await pg.locator('table.grid').count()==1,'예약판 표시')
        # 다음 주로
        await pg.click('[data-act=week][data-d="7"]')
        k='p_hall|2026-11-30|1'
        await pg.click(f'[data-k="{k}"].cell'); 
        ok('체육 수업' in await pg.inner_text('.modal'),'체육 칸 모달')
        await pg.click('[data-act=release]'); await pg.wait_for_timeout(100)
        await pg.click('[data-act=close]')
        txt=await pg.inner_text(f'[data-k="{k}"].cell')
        ok('빈 칸' in txt and '체육 비움' in txt,'비운 칸이 입찰 중으로: '+txt.replace('\n',' '))
        # 6-2 는 이번 달 이미 한 번 사용(바로 예약 기록 넣기)
        await pg.evaluate("""window.__jjim.store().update(s=>{s.bookings['p_multi|2026-11-02|1']={teacherId:'t_62',who:'6-2',how:'direct',at:'x'};s.bookings['p_multi|2026-11-03|1']={teacherId:'t_62',who:'6-2',how:'direct',at:'x'}})""")
        for name in ['강노을','최들꽃']:
            await login(name); await pg.click('[data-act=week][data-d="7"]')
            await pg.click(f'[data-k="{k}"].cell'); await pg.click('[data-act=bid]'); await pg.wait_for_timeout(100); await pg.click('[data-act=close]')
        n=await pg.evaluate(f"window.__jjim.S.bids['{k}'].length")
        ok(n==2,'두 반 신청')
        # 중복 신청 막기
        r=await pg.evaluate(f"window.__jjim.store().update(s=>window.__jjim.A.bid(s,s.teachers.find(t=>t.id==='t_41'),'{k}'))")
        ok(r.get('error') is not None,'중복 신청 막힘')
        dl=await pg.evaluate("window.__jjim.deadlineOf('2026-11-30').toString()")
        ok('Fri Nov 27 2026 15:00' in dl,'월요일 칸 마감은 금요일 15시: '+dl[:24])
        # 마감 1분 전: 아직 미정
        await pg.evaluate("window.__jjim.setNow('2026-11-27T14:59:00')"); await pg.wait_for_timeout(200)
        ok(await pg.evaluate(f"!window.__jjim.S.bookings['{k}']"),'마감 전 미정')
        await pg.evaluate("window.__jjim.setNow('2026-11-27T15:00:30')"); await pg.wait_for_timeout(300)
        bk=await pg.evaluate(f"window.__jjim.S.bookings['{k}']")
        ok(bk and bk['who']=='4-1','덜 쓴 반(4-1) 확정: '+str(bk))
        msgs=await pg.evaluate("window.__jjim.S.messages.filter(m=>m.to==='t_62').map(m=>m.text)")
        ok(any('아쉬워요' in m for m in msgs),'진 반에 알림')
        # 알림 배지 (지금 최들꽃)
        badge=await pg.locator('.badge').count()
        ok(badge>=1,'알림 배지 표시')
        await pg.click('[data-act=view][data-v=inbox]'); await pg.wait_for_timeout(200)
        ok('[확정]' in await pg.inner_text('main'),'알림함에 확정 메시지')
        ok(await pg.locator('.badge').count()==0,'읽으면 배지 사라짐')
        # 동점 추첨: 화요일 3교시 다목적실(3-1 이미 신청) + 3-2 신청, 둘 다 0회
        k2='p_multi|2026-12-01|3'
        await pg.evaluate("window.__jjim.setNow('2026-11-26T10:00:00')")
        await pg.evaluate(f"""window.__jjim.store().update(s=>{{s.bids['{k2}']=[{{teacherId:'t_31',who:'3-1',at:'x'}},{{teacherId:'t_32',who:'3-2',at:'x'}}]}})""")
        await pg.evaluate("window.__jjim.setNow('2026-11-30T15:01:00')"); await pg.wait_for_timeout(300)
        bk2=await pg.evaluate(f"window.__jjim.S.bookings['{k2}']")
        ok(bk2 and bk2['who'] in ('3-1','3-2'),'동점 추첨 확정: '+str(bk2 and bk2['who']))
        # 같은 상황을 다시 정리해도 같은 결과인지(결정적)
        same=await pg.evaluate(f"""(()=>{{const J=window.__jjim; const s={{...JSON.parse(JSON.stringify(J.S))}}; delete s.bookings['{k2}']; s.bids['{k2}']=[{{teacherId:'t_32',who:'3-2'}},{{teacherId:'t_31',who:'3-1'}}]; J.resolveDue(s,new Date('2026-11-30T15:01:00')); return s.bookings['{k2}'].who}})()""")
        ok(same==bk2['who'],'추첨 결과가 순서와 관계없이 같음')
        # 바로 예약: 마감 지난 빈 칸 (12/1 화 5교시 강당 - 체육 없음)
        await login('이하늘')
        k3='p_hall|2026-12-01|5'
        info=await pg.evaluate(f"window.__jjim.slotInfo(window.__jjim.S,'p_hall','2026-12-01',5).st")
        ok(info=='direct','마감 지난 빈 칸은 바로 예약: '+info)
        await pg.click(f'[data-k="{k3}"].cell'); await pg.click('[data-act=direct]'); await pg.wait_for_timeout(100)
        ok(await pg.evaluate(f"window.__jjim.S.bookings['{k3}'].who")=='3-1','바로 예약 성공')
        await pg.click('[data-act=close]')
        # 우천: 12/1(화) 1교시 운동장 4-1 체육, 그 시간 강당은? 화 1교시 강당 비어있음 → 3-2가 바로 예약해 둠
        await login('박바다'); 
        await pg.evaluate("window.__jjim.store().update(s=>window.__jjim.A.direct(s,s.teachers.find(t=>t.id==='t_32'),'p_hall|2026-12-01|1'))")
        ok(await pg.evaluate("window.__jjim.S.bookings['p_hall|2026-12-01|1'].who")=='3-2','3-2 강당 1교시 예약')
        await login('김체육'); await pg.click('[data-act=place][data-id=p_field]')
        await pg.click('[data-k="p_field|2026-12-01|1"].cell')
        await pg.click('[data-act=rainpick]'); await pg.wait_for_timeout(100)
        mt=await pg.inner_text('.modal')
        ok('3-2 예약 있음' in mt,'우천 선택창에 기존 예약 안내')
        await pg.click('[data-act=raindo][data-to=p_hall]'); await pg.wait_for_timeout(200)
        bk=await pg.evaluate("window.__jjim.S.bookings['p_hall|2026-12-01|1']")
        ok(bk['how']=='rain' and bk['who']=='4-1','우천으로 4-1이 강당 차지')
        m32=await pg.evaluate("window.__jjim.S.messages.filter(m=>m.to==='t_32').map(m=>m.text).join('|')")
        ok('우천 안내' in m32 and '취소' in m32,'밀려난 담임(3-2)에게 안내')
        m41=await pg.evaluate("window.__jjim.S.messages.filter(m=>m.to==='t_41').map(m=>m.text).join('|')")
        ok('강당에서 해요' in m41,'4-1 담임에게 장소 변경 안내')
        ft=await pg.inner_text('[data-k="p_field|2026-12-01|1"].cell')
        ok('우천' in ft,'운동장 칸에 우천 표시')
        # 다른 체육 수업이 있는 실내로는 못 옮김: 12/3(목) 3교시 운동장 4-2? 목 3교시는 강당 4-2. 목1교시 운동장 6-1, 강당 비어있음 OK. 
        r=await pg.evaluate("window.__jjim.store().update(s=>window.__jjim.A.rain(s,s.teachers[0],'p_field|2026-12-03|1','p_field'))")
        ok(r.get('error') is not None,'실외로 우천 이동 막힘')
        # 금 3교시 운동장 6-1 → 강당 3교시? 금 강당 p5 4-1, p1 3-1,p2 3-2. 수 3교시 운동장 3-2 → 강당 수3교시? 수 강당 p1 5-1 p2 5-2 p4 4-1 → p3 free. Thu p1 field 6-1 -> hall Thu p1? Thu hall p3 4-2.
        # 목 5교시 운동장 5-1 → 강당 목5 비어있음 OK; 화 5교시 운동장 3-1 → 강당 화5 = 이하늘 바로예약(3-1)
        r=await pg.evaluate("window.__jjim.store().update(s=>window.__jjim.A.rain(s,s.teachers[0],'p_field|2026-12-04|3','p_hall'))")
        ok(r.get('ok'),'금 3교시 운동장→강당 이동 가능')
        # 되돌리기
        await pg.click('[data-act=close]') if await pg.locator('[data-act=close]').count() else None
        await pg.click('[data-k="p_field|2026-12-01|1"].cell'); await pg.click('[data-act=rainundo]'); await pg.wait_for_timeout(100)
        ok(await pg.evaluate("!window.__jjim.S.bookings['p_hall|2026-12-01|1'] && !window.__jjim.S.rain['p_field|2026-12-01|1']"),'우천 되돌리기')
        # 되돌리기: 비운 칸 다시 체육으로 (입찰자 알림)
        await pg.evaluate("window.__jjim.setNow('2026-12-01T09:00:00')")
        kr='p_hall|2026-12-07|2'
        await pg.evaluate(f"window.__jjim.store().update(s=>window.__jjim.A.release(s,s.teachers[0],'{kr}'))")
        await pg.evaluate(f"window.__jjim.store().update(s=>window.__jjim.A.bid(s,s.teachers.find(t=>t.id==='t_51'),'{kr}'))")
        r=await pg.evaluate(f"window.__jjim.store().update(s=>window.__jjim.A.unrelease(s,s.teachers[0],'{kr}'))")
        ok(r.get('ok') and await pg.evaluate(f"!window.__jjim.S.bids['{kr}']"),'다시 체육으로 되돌리면 입찰 취소')
        ok(await pg.evaluate("window.__jjim.S.messages.some(m=>m.to==='t_51'&&m.text.includes('체육 수업으로 다시'))"),'입찰자에게 취소 알림')
        # 담임은 체육 칸 비우기 못함
        r=await pg.evaluate("window.__jjim.store().update(s=>window.__jjim.A.release(s,s.teachers.find(t=>t.id==='t_51'),'p_hall|2026-12-07|1'))")
        ok(r.get('error') is not None,'담임은 체육 칸 못 비움')
        # 설정: 장소 추가 + 시간표
        await pg.click('[data-act=view][data-v=settings]'); await pg.wait_for_timeout(100)
        await pg.fill('#new-place','탁구장'); await pg.click('[data-act=place-add]'); await pg.wait_for_timeout(100)
        ok(await pg.evaluate("window.__jjim.S.places.some(p=>p.name==='탁구장')"),'장소 추가')
        pid=await pg.evaluate("window.__jjim.S.places.find(p=>p.name==='탁구장').id")
        await pg.click(f'[data-act=ttplace][data-id="{pid}"]')
        await pg.select_option(f'[data-tt="{pid}|1|1"]','5-2'); await pg.wait_for_timeout(150)
        ok(await pg.evaluate(f"window.__jjim.S.peTimetable['{pid}|1|1'].cls")=='5-2','시간표 넣기')
        await pg.click('[data-act=view][data-v=board]'); await pg.click(f'[data-act=place][data-id="{pid}"]')
        await pg.click('[data-act=week][data-d="7"]')
        ok('5-2' in await pg.inner_text('[data-k="%s|2026-12-07|1"].cell'%pid),'새 장소에 체육 칸 자동')
        # 교시 추가
        await pg.click('[data-act=view][data-v=settings]'); await pg.click('[data-act=per-add]'); await pg.wait_for_timeout(100)
        ok(await pg.evaluate("window.__jjim.S.school.periods.length")==7,'교시 더하기')
        await pg.click('[data-act=view][data-v=mine]'); ok('내가 비운' in await pg.inner_text('main'),'내 예약 화면(체육)')
        # 모바일 화면
        # 점심시간
        await pg.click('[data-act=view][data-v=board]'); await pg.click('[data-act=place][data-id=p_hall]')
        await pg.evaluate("window.__jjim.setNow('2026-12-01T09:00:00')"); await pg.click('[data-act=week][data-d="0"]')
        ok(await pg.locator('tr.lunchrow').count()==1,'강당에 점심시간 줄')
        await pg.click('[data-act=place][data-id=p_field]')
        ok(await pg.locator('tr.lunchrow').count()==0,'운동장에는 점심시간 줄 없음')
        kl='p_hall|2026-12-03|0'
        r=await pg.evaluate(f"window.__jjim.store().update(s=>window.__jjim.A.bid(s,s.teachers.find(t=>t.id==='t_en'),'{kl}'))")
        ok(r.get('error') is not None,'교과 선생님은 점심시간 신청 못함')
        r=await pg.evaluate(f"window.__jjim.store().update(s=>window.__jjim.A.bid(s,s.teachers.find(t=>t.id==='t_pe'),'{kl}'))")
        ok(r.get('error') is not None,'체육 선생님도 점심시간 신청 못함')
        # 6-1은 수업 시간을 많이 썼지만 점심시간은 0회, 6-2는 점심시간 1회
        await pg.evaluate("""window.__jjim.store().update(s=>{for(let d=2;d<=5;d++) s.bookings['p_multi|2026-12-0'+d+'|6']={teacherId:'t_61',who:'6-1',how:'direct',at:'x'}; s.bookings['p_hall|2026-12-01|0']={teacherId:'t_62',who:'6-2',how:'direct',at:'x'};})""")
        for tid in ['t_61','t_62']:
            r=await pg.evaluate(f"window.__jjim.store().update(s=>window.__jjim.A.bid(s,s.teachers.find(t=>t.id==='{tid}'),'{kl}'))")
            ok(r.get('ok'),'담임 점심시간 신청 '+tid)
        await pg.evaluate("window.__jjim.setNow('2026-12-02T15:00:30')"); await pg.wait_for_timeout(300)
        bk=await pg.evaluate(f"window.__jjim.S.bookings['{kl}']")
        ok(bk and bk['who']=='6-1','점심시간은 점심시간 사용 횟수로만 비교(6-1 확정): '+str(bk and bk['who']))
        msg=await pg.evaluate("window.__jjim.S.messages.filter(m=>m.to==='t_61').map(m=>m.text).join('|')")
        ok('정리와 안전 지도' in msg,'확정 알림에 정리·안전 지도 안내')
        await login('윤새벽'); await pg.click('[data-act=place][data-id=p_hall]')
        await pg.click(f'[data-k="{kl}"].cell'); mt=await pg.inner_text('.modal')
        ok('점심시간' in mt and '안전 지도' in mt,'점심시간 칸 창에 안내')
        await pg.click('[data-act=close]')
        # 설정에서 점심시간 끄기
        await login('김체육'); await pg.click('[data-act=view][data-v=settings]')
        await pg.uncheck('#lu-on'); await pg.click('[data-act=save-lunch]'); await pg.wait_for_timeout(150)
        await pg.click('[data-act=view][data-v=board]'); await pg.click('[data-act=place][data-id=p_hall]')
        ok(await pg.locator('tr.lunchrow').count()==0,'점심시간 끄면 줄 사라짐')
        ok(not errs,'콘솔 오류 없음 '+str(errs[:3]))
        await b.close()
    print('FAILS',len(fails))
    if fails: raise SystemExit(1)
asyncio.run(main())
