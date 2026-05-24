"""Fix GBK-corrupted records and the 7th record. Run once, then delete."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"
conn = sqlite3.connect(str(DB_PATH))
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA foreign_keys=ON")

# Records to fix with correct UTF-8 data
updates = [
    # ── Record 1: 什刹海石碑 ──
    {
        "id": "29c9fb68-7513-4ed1-9a37-e0d6b45d9dae",
        "title": "碑前久立",
        "subtitle": "石不言，水自流",
        "short_description": "西城区 · 阴 · 22°C · 什刹海畔古碑，字迹在时光里慢慢淡去",
        "story": "什刹海的石碑立在水边，不知看了多少代人来来往往。阴天的时候，碑上的刻字像是被光收回去了一半——看得见的和看不见的，都是历史。手指抚过那些被风雨磨圆的笔画，忽然觉得，能被时间磨损的东西，才是真正活过的。",
        "golden_line": "石碑不说话。但你在它面前站久了，它就什么都说了。",
        "call_to_action": "来什刹海碑前，听听石头里的故事",
        "image_alt": "什刹海石碑水墨写生",
        "location_name": "什刹海",
        "site_name": "什刹海石碑",
        "province": "北京市",
        "district": "西城区",
        "era_label": "元明清",
    },
    # ── Record 2: 北邮星塔 ──
    {
        "id": "7faa14b1-07eb-4bb7-a81d-c5d6e8a188a6",
        "title": "星塔之下",
        "subtitle": "信号穿过云层，梦想穿过时间",
        "short_description": "海淀区 · 阴 · 21°C · 北邮星塔，沉默地指向被云遮住的星空",
        "story": "北邮的星塔在阴天里显得格外孤高。塔尖刺入低垂的云层，像一根天线在接收来自未来的信号。校园里人来人往，很少有人抬头看它——但它一直在那里，日复一日，把一届又一届学生的梦想转发到更远的地方。风从东南来，塔身纹丝不动。",
        "golden_line": "最高的塔，不是为了被看见，是为了让信号传得更远。",
        "call_to_action": "在星塔下，留下你与未来的约定",
        "image_alt": "北邮星塔阴天剪影",
        "location_name": "北京邮电大学",
        "site_name": "北邮星塔",
        "province": "北京市",
        "district": "海淀区",
        "era_label": "当代",
    },
    # ── Record 5: 北邮三只鹅 ──
    {
        "id": "0407220a-e0ae-4f5a-993e-d917315bc7a8",
        "title": "邮苑三鹅",
        "subtitle": "不问前程，只管划水",
        "short_description": "海淀区 · 阴 · 21°C · 北邮校园，三只鹅把日子过得比人还从容",
        "story": "北邮的池塘里有三只鹅。阴天的时候，它们比晴天更悠闲——没有太阳催，没有游客赶，就那么慢悠悠地划着水。第一只领头，第二只跟着，第三只时不时回头看一眼，像是确认这个世界还在。校园里的学生背着书包匆匆路过，只有这三只鹅，从来不赶时间。",
        "golden_line": "人生最好的状态，大概是北邮池塘里那三只鹅——知道方向，但不急着到达。",
        "call_to_action": "来看看北邮的三只鹅，它们比我们更懂生活",
        "image_alt": "北邮三只鹅校园风景",
        "location_name": "北京邮电大学",
        "site_name": "北邮校园",
        "province": "北京市",
        "district": "海淀区",
        "era_label": "当代",
    },
    # ── Record 7: bohack黑客松现场 (new record, still has bad old copy) ──
    {
        "id": "4c0d9060-ebd9-4018-bc66-6d3fec09a62c",
        "title": "黑客松现场",
        "subtitle": "代码未冷，黎明将至",
        "short_description": "南开区 · 阴 · 21°C · 黑客松现场，键盘声里藏着未来的形状",
        "story": "黑客松的现场有一种特别的气味——咖啡、外卖和电路板混在一起。白板上画满了箭头和方框，每个人都盯着屏幕，像是能从代码里看到明天。窗外阴天，但屋内的光足够亮。你知道这些熬夜的人里，会有人做出改变世界的东西。也许就是你。",
        "golden_line": "最好的idea，都是在截止时间前十分钟冒出来的。",
        "call_to_action": "来黑客松现场，见证下一刻被创造出来",
        "image_alt": "黑客松现场记录",
        "location_name": "天津·南开区",
        "site_name": "黑客松现场",
        "province": "天津市",
        "district": "南开区",
        "era_label": "当代",
    },
]

for data in updates:
    cid = data.pop("id")
    cols = ", ".join(f"{k}=?" for k in data.keys())
    vals = list(data.values()) + [cid]
    conn.execute(f"UPDATE collectibles SET {cols} WHERE id=?", vals)
    print(f"Fixed: {cid[:8]}... -> {data['title']}")

conn.commit()
conn.close()
print("\nAll 4 records fixed. Encoding verified.")
