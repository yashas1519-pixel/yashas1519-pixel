"""Render the reference-inspired isometric activity panel. Real data only in --live mode."""
import argparse, datetime as dt, json, math, os, urllib.request, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]; ASSETS=ROOT/'assets'

def live_days(user):
    token=os.environ.get('PROFILE_ACTIVITY_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token: raise RuntimeError('GitHub token required')
    end=dt.datetime.now(dt.timezone.utc); start=end-dt.timedelta(days=181)
    q='''query($login:String!, $from:DateTime!, $to:DateTime!) { user(login:$login) { contributionsCollection(from:$from,to:$to) { contributionCalendar { totalContributions weeks { contributionDays { date weekday contributionCount } } } } } }'''
    v={'login':user,'from':start.isoformat(),'to':end.isoformat()}
    req=urllib.request.Request('https://api.github.com/graphql',data=json.dumps({'query':q,'variables':v}).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','User-Agent':'offscreen-editorial-readme'})
    with urllib.request.urlopen(req,timeout=30) as res: body=json.load(res)
    if body.get('errors'): raise RuntimeError('GitHub GraphQL request failed: '+str(body['errors']))
    calendar=body['data']['user']['contributionsCollection']['contributionCalendar']
    return [(d['date'],d['weekday'],int(d['contributionCount'])) for w in calendar['weeks'] for d in w['contributionDays']],end.date().isoformat()

def font(size,bold=False):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)

def shade(c,f): return tuple(max(0,min(255,round(v*f))) for v in c)

def render(days,date,out,mode):
    base=Image.open(ASSETS/'activity-base.png').convert('RGB'); dates={d:c for d,_,c in days}; weeks=26
    today=dt.date.fromisoformat(date); sunday=today-dt.timedelta(days=(today.weekday()+1)%7); first=sunday-dt.timedelta(weeks=weeks-1)
    data=[]
    for x in range(weeks):
        for y in range(7):
            day=first+dt.timedelta(days=x*7+y)
            if day<=today: data.append((x,y,dates.get(day.isoformat(),0)))
    total=sum(v for _,_,v in data); maxv=max([1]+[v for _,_,v in data]); frames=[]
    # Ordered back to front. Each bar's height represents the count on that date.
    for frame in range(20):
        pic=base.copy(); d=ImageDraw.Draw(pic); sweep=(frame/19)*(weeks+10)-5
        for x,y,n in sorted(data,key=lambda a:(a[0]+a[1],a[0])):
            u=150+x*17-y*17; v=240+x*7+y*11
            # shift far weeks upward to resemble the reference's diagonal display
            u=145+x*17-y*17; v=430-x*7+y*11
            h=0 if n==0 else 10+int(85*math.sqrt(n/maxv)); light=max(0,1-abs(x-sweep)/3)
            c=(29,43,31) if n==0 else (int(76+104*math.sqrt(n/maxv)),int(130+100*math.sqrt(n/maxv)),int(24+40*math.sqrt(n/maxv)))
            c=shade(c,1+.35*light)
            top=[(u,v-h-7),(u+14,v-h),(u,v-h+7),(u-14,v-h)]
            if h:
                d.polygon([top[3],top[2],(u,v+7),(u-14,v)],fill=shade(c,.52))
                d.polygon([top[1],top[2],(u,v+7),(u+14,v)],fill=shade(c,.77))
            d.polygon(top,fill=c,outline=shade(c,1.25))
        # Actual counts only, with a distinct label in preview mode.
        status=f'{total:,} contributions · last 26 weeks' if mode=='live' else ('DEMO DATA · animated preview' if mode=='demo' else 'Waiting for the first GitHub sync')
        d.text((33,520),status,font=font(21,True),fill='#ceef89' if mode!='demo' else '#e2d8bd')
        d.text((33,550),f'Updated {date} · daily sync' if mode=='live' else ('Illustration — not actual account activity' if mode=='demo' else 'Run the Activity workflow to load real data'),font=font(15),fill='#c0c5c3')
        frames.append(pic.quantize(colors=128,method=Image.Quantize.MEDIANCUT))
    frames[0].save(out,save_all=True,append_images=frames[1:],duration=115,loop=0,optimize=True,disposal=2)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['live','demo','empty'],default='live');p.add_argument('--user',default='yashas1519-pixel');p.add_argument('--output',default=str(ASSETS/'activity.gif'));args=p.parse_args()
    today=dt.datetime.now(dt.timezone.utc).date(); date=today.isoformat(); days=[]
    if args.mode=='live': days,date=live_days(args.user)
    elif args.mode=='demo':
        rng=random.Random(41)
        for i in range(182):
            day=today-dt.timedelta(days=i); days.append((day.isoformat(),(day.weekday()+1)%7,rng.choices([0,1,2,4,7,12],[45,20,16,10,6,3])[0]))
    render(days,date,args.output,args.mode)
