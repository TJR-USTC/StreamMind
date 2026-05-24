# -*- coding: utf-8 -*-
"""模拟数据生成器 — 12维版"""
import time
from typing import Dict, List
from config import CATEGORIES, RNG, LATENT_DIM
from models import VideoMeta, UserProfile, UserBehavior

FRAME_POOL = {
    "知识干货": [
        "翻开一本书阅读", "白板上画思维导图", "电脑屏幕展示数据图表",
        "展示实验过程", "3D动画演示原理", "对比案例左右分屏",
        "真人出镜讲解知识", "字幕要点高亮标注", "问答互动环节",
        "总结金句字幕展示",
    ],
    "游戏娱乐": [
        "打开游戏主界面", "选择角色和阵容", "加载对局地图",
        "激烈团战画面", "精彩操作慢放回放", "拿下击杀提示",
        "逆风翻盘时刻", "装备展示面板", "结算胜利画面",
        "主播直播间镜头反应",
    ],
    "美食探店": [
        "人走进厨房打开冰箱", "取出食材放在案板上", "用刀熟练切菜",
        "热油下锅发出滋滋声", "翻炒食材冒热气", "调味料撒入锅中",
        "色香味俱全的成品特写", "夹起一块展示细节", "出锅装盘摆造型",
        "第一人称试吃表情",
    ],
    "科技数码": [
        "拆开产品包装盒", "产品外观360度展示", "开机启动界面",
        "跑分软件测试画面", "对比新旧款参数图表", "实际使用场景演示",
        "发热温度测试", "续航时间实测", "优缺点总结字幕",
        "购买建议二维码展示",
    ],
    "户外旅行": [
        "飞机起飞窗外云层", "到达目的地车站机场", "拖着行李箱走在街上",
        "无人机航拍全景", "日出日落延时摄影", "海浪拍打礁石",
        "走在古镇石板路上", "山顶俯瞰云海", "搭帐篷露营",
        "品尝当地特色小吃",
    ],
    "萌宠日常": [
        "人牵狗走在街上", "狗在草地奔跑嬉戏", "猫咪趴在窗台上晒太阳",
        "主人拿出零食引诱", "宠物激动地摇尾巴", "喂食特写镜头",
        "宠物做出搞笑动作", "两只宠物互相追逐", "宠物睡觉打呼噜",
        "给宠物洗澡吹干毛发",
    ],
    "情感心理": [
        "一个人独坐在窗边思考", "翻看手机聊天记录", "两人牵手走在夕阳下",
        "拥抱安慰哭泣的朋友", "心理咨询师对话场景", "写下内心感想的笔记本",
        "放松冥想的特写", "微笑释然的慢镜头", "雨水打在玻璃上的意境",
        "阳光洒进房间的温暖画面",
    ],
    "穿搭美妆": [
        "衣帽间挑选衣服", "对着镜子试穿搭配", "化妆品平铺展示",
        "化妆刷上妆特写", "口红试色对比", "全身镜前转圈展示",
        "不同风格对比切换", "出门街拍镜头", "卸妆护肤步骤",
        "最终妆容特写定格",
    ],
    "运动健身": [
        "穿运动鞋系鞋带", "跑步机上有氧热身", "哑铃力量训练",
        "瑜伽垫上核心训练", "跳绳燃脂特写", "健身餐准备过程",
        "汗水滴落慢镜头", "肌肉线条展示", "体重秤数字变化",
        "拉伸放松收尾",
    ],
    "影视八卦": [
        "电影海报特写", "精彩片段剪辑混剪", "角色对话名场面",
        "弹幕吐槽实时滚动", "剧组花絮NG镜头", "明星采访片段",
        "粉丝见面会现场", "热搜话题大字幕", "剧透预警提示",
        "下期预告彩蛋",
    ],
    "职场提升": [
        "简历修改对比", "模拟面试场景", "PPT演示汇报",
        "团队会议讨论", "时间管理工具展示", "技能证书特写",
        "办公桌整理前后对比", "升职加薪通知截图", "职场社交场景",
        "职业规划思维导图",
    ],
    "家居生活": [
        "进入装修好的新家", "客厅沙发摆放展示", "厨房收纳整理过程",
        "智能家居语音控制", "绿植浇水特写", "香薰蜡烛点燃",
        "窗边阅读温馨画面", "周末大扫除快进", "阳台花园布置",
        "夜晚灯光氛围全景",
    ],
}

COMMENT_POOL = [
    "太可爱了吧", "看着就饿了", "学到了学到了", "这也太好笑了",
    "主播好厉害", "想去这个地方", "收藏了收藏了", "这个真的好用",
    "笑死我了", "绝绝子", "码住码住", "这是我的菜",
    "已下单", "求链接", "良心推荐", "看哭了",
    "太美了吧", "好治愈", "硬核干货", "原来是这样",
    "支持支持", "爱了爱了", "感谢分享", "期待下一期",
    "涨知识了", "笑不活了", "说得太对了", "第一次见",
    "好有道理", "马上去试", "太真实了", "同款同款",
]

PREFIXES = ["快乐", "懒懒", "追风", "甜心", "佛系", "沙雕", "文艺", "干饭", "摸鱼", "卷王"]
SUFFIXES = ["小王子", "少女", "阿宅", "大叔", "一枚", "同学", "铁粉", "玩家", "爱好者", "收藏家"]


def video_category(video_id: str) -> str:
    idx = int(video_id.split("_")[1]) % len(CATEGORIES)
    return CATEGORIES[idx]


class MockDataGenerator:
    def make_videos(self, count: int = 100) -> List[VideoMeta]:
        videos = []
        for i in range(count):
            cat = CATEGORIES[i % len(CATEGORIES)]
            pool = FRAME_POOL[cat]
            k = RNG.randint(3, min(8, len(pool)))
            frames = RNG.sample(pool, k=k)
            author_pool = [f"{cat}博主", f"{cat}达人", f"资深{cat}爱好者"]
            videos.append(VideoMeta(
                video_id=f"vid_{i:04d}",
                frame_descriptions=frames,
                author_tags=RNG.sample(author_pool, k=RNG.randint(1, min(3, len(author_pool)))),
                duration_sec=RNG.randint(10, 600),
            ))
        return videos

    def make_users(self, count: int = 100) -> List[UserProfile]:
        import random as _r
        rng = _r.Random()
        weights = [0.22, 0.18, 0.14, 0.10, 0.08, 0.06, 0.05, 0.04, 0.04, 0.03, 0.03, 0.03]
        users = []
        for i in range(count):
            # 每人4~6个关注话题 → 增强用户间关联度和画像丰富度
            n_dom = rng.randint(4, 6)
            doms = []
            remaining_weights = weights[:]
            for _ in range(n_dom):
                total_w = sum(remaining_weights)
                if total_w <= 0: break
                idx = rng.choices(range(LATENT_DIM), weights=[w/total_w for w in remaining_weights])[0]
                doms.append(idx)
                remaining_weights[idx] = 0
            vec = [0.005] * LATENT_DIM
            # 主导权重递减: 0.4 > 0.25 > 0.15 > 0.1 > 0.06 > 0.035
            base_weights = [0.40, 0.25, 0.15, 0.10, 0.06, 0.035]
            for j, di in enumerate(doms):
                bw = base_weights[min(j, len(base_weights)-1)]
                vec[di] = rng.uniform(bw * 0.8, bw * 1.2)
            total = sum(vec)
            vec = [round(v / total, 4) for v in vec]
            users.append(UserProfile(
                user_id=f"uid_{i:04d}",
                username=RNG.choice(PREFIXES) + "的" + RNG.choice(SUFFIXES),
                persona_vector=vec,
                last_update_time=time.time(),
            ))
        return users

    def make_behaviors(self, users: List[UserProfile],
                       video_count: int) -> Dict[str, List[UserBehavior]]:
        bhv = {}
        for u in users:
            visit_rate = RNG.uniform(0.3, 0.75)
            blist = []
            for j in range(video_count):
                vid = f"vid_{j:04d}"
                if RNG.random() >= visit_rate:
                    blist.append(UserBehavior(user_id=u.user_id, video_id=vid))
                    continue
                r = RNG.random()
                if r < 0.35: wr = RNG.randint(80, 100)
                elif r < 0.55: wr = RNG.randint(40, 79)
                elif r < 0.75: wr = RNG.randint(20, 39)
                else: wr = RNG.randint(1, 19)
                bp = wr / 100.0
                blist.append(UserBehavior(
                    user_id=u.user_id, video_id=vid, is_visited=True,
                    watch_ratio=wr,
                    is_liked=RNG.random() < (bp * 0.5),
                    is_favorited=RNG.random() < (bp * 0.3),
                    is_followed=RNG.random() < (bp * 0.05),
                    is_commented=RNG.random() < (bp * 0.12),
                    comment_text=RNG.choice(COMMENT_POOL) if RNG.random() < (bp * 0.12) else "",
                ))
            bhv[u.user_id] = blist
        return bhv
