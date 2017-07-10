import json
import time
import hashlib
import sqlite3
from urllib import parse
from pymysql import escape_string


def game_db_init():
    global live_setting_id, unit_db
    unit_db = sqlite3.connect("./db/unit/unit.db_", check_same_thread=False)
    battle = sqlite3.connect("./db/event/battle.db_").execute(
        "SELECT live_difficulty_id,live_setting_id FROM event_battle_live_m").fetchall()
    festival = sqlite3.connect("./db/event/festival.db_").execute(
        "SELECT live_difficulty_id,live_setting_id FROM event_festival_live_m").fetchall()
    marathon = sqlite3.connect("./db/event/marathon.db_").execute(
        "SELECT live_difficulty_id,live_setting_id FROM event_marathon_live_m").fetchall()
    challenge = sqlite3.connect("./db/challenge/challenge.db_").execute(
        "SELECT live_difficulty_id,live_setting_id FROM event_challenge_live_m").fetchall()
    live_db = sqlite3.connect("./db/live/live.db_")
    live_setting_normal = live_db.execute("SELECT live_difficulty_id,live_setting_id FROM normal_live_m").fetchall()
    live_setting_special = live_db.execute("SELECT live_difficulty_id,live_setting_id FROM special_live_m").fetchall()
    ress = []
    ress.extend(live_setting_normal)
    ress.extend(live_setting_special)
    ress.extend(marathon)
    ress.extend(battle)
    ress.extend(festival)
    ress.extend(challenge)
    live_setting_id = dict(ress)


def get_setting_id(live_difficulty_id):
    try:
        return live_setting_id[live_difficulty_id]
    except KeyError:
        game_db_init()
        try:
            return live_setting_id[live_difficulty_id]
        except KeyError:
            return 'null'


def add_user(user_info_source):
    user = user_info_source["res_data"]["user"]

    sql = """
    INSERT INTO `llproxy`.`users` (
    	`uid`, `name`, `token`, 
    	`level`, `invite_code`, `update_time`
    ) 
    VALUES 
    	(
    		'{uid}', '{name}', '{token}', 
    		'{level}', '{invite_code}', '{update_time}'
    	)
    ON DUPLICATE KEY UPDATE `name`=VALUES(`name`),`token`=VALUES(`token`),`level`=VALUES(`level`),
    `invite_code`=VALUES(`invite_code`),`update_time`=VALUES(`update_time`);
        """.format(
        uid=user["user_id"],
        name=escape_string(user['name']),
        level=user["level"],
        token=user_info_source["token"],
        invite_code=user["invite_code"],
        update_time=timestamp()
    )

    return sql,


def update_user(dict):
    sql = []

    if 'name' in dict:
        sqln = """
        INSERT INTO `llproxy`.`users` (
        	`uid`, `name`, `update_time`
        ) 
        VALUES 
        	(
        		'{uid}', '{name}', '{update_time}'
        	)
        ON DUPLICATE KEY UPDATE `name`=VALUES(`level`),update_time=VALUES(update_time);
        """.format(
            uid=dict["uid"],
            name=escape_string(dict["name"]),
            update_time=timestamp()
        )
        sql.append(sqln)
    if 'level' in dict:
        sqln = """
        INSERT INTO `llproxy`.`users` (
        	`uid`, `level`, `update_time`
        ) 
        VALUES 
        	(
        		'{uid}', '{level}', '{update_time}'
        	)
        ON DUPLICATE KEY UPDATE `level`=VALUES(`level`),update_time=VALUES(update_time);
            """.format(
            uid=dict["uid"],
            level=dict["level"],
            update_time=timestamp()
        )
        sql.append(sqln)
    if 'login_key' in dict:
        sqln = """
        INSERT INTO `llproxy`.`users` (
        	`uid`, `login_key`, `update_time`
        ) 
        VALUES 
        	(
        		'{uid}', '{login_key}', '{update_time}'
        	)
        ON DUPLICATE KEY UPDATE `login_key`=VALUES(login_key),update_time=VALUES(update_time);
            """.format(
            uid=dict["uid"],
            login_key=dict["login_key"],
            update_time=timestamp()
        )
        sql.append(sqln)
    return sql


def replace_unit(uid, unit_info_array):
    sql = []
    sql0 = "DELETE FROM unit_unitAll  WHERE status = 0"
    sql1 = "UPDATE unit_unitAll set status=0 WHERE uid=%s" % uid

    keysl = list(unit_info_array[0].keys())
    keys = "(`uid`,`update_time`,`status`,`unit_number`, `unit_type_id`, `rarity`, `attribute_id`, " + ",".join(
        keysl) + ")"
    valuesl = []
    cur = unit_db.cursor()
    for i in unit_info_array:
        unit_id = i['unit_id']
        cur.execute("SELECT unit_number,unit_type_id,rarity,attribute_id FROM unit_m WHERE unit_id = %s" % unit_id)
        u = cur.fetchone()
        s = "('{}','{}','{}','{}','{}','{}','{}'".format(uid, timestamp(), 1, u[0], u[1], u[2], u[3])
        for k in i.values():
            if k is True:
                k = 1
            elif k is False:
                k = 0
            s += ",'%s'" % k

        s += ")"
        valuesl.append(s)

    values = ",".join(valuesl)

    sql2 = """
        REPLACE INTO `llproxy`.`unit_unitAll`
        {}
        VALUES
        {}
        """.format(keys, values)
    sql3 = """
                INSERT INTO `llproxy`.`deck_and_removable_Info` (`uid`, `update_time`, `unit_info`) 
                VALUES ('{}', '{}', '{}')
                ON DUPLICATE KEY UPDATE `unit_info`=VALUES(unit_info),update_time=VALUES(update_time);
                """.format(uid, timestamp(),
                           escape_string(json.dumps(unit_info_array, separators=(',', ':'), ensure_ascii=False)))

    sql.append(sql0)
    sql.append(sql1)
    sql.append(sql2)
    sql.append(sql3)
    return sql


def score_match_status_0(uid, event_id, room_id, res):
    sql = []

    total_event_point = 0
    event_rank = 0
    unit_id = 0
    display_rank = 1
    setting_award_id = 1
    playes = []
    for u in res['matching_user']:
        if 'user_info' in u:
            user_id = u['user_info']['user_id']
            playes.append(str(user_id))
            if user_id == uid:
                total_event_point = u['event_status']['total_event_point']
                event_rank = u['event_status']['event_rank']
                unit_id = u['center_unit_info']['unit_id']
                display_rank = u['center_unit_info']['display_rank']
                setting_award_id = u['setting_award_id']
    setting_id = get_setting_id(res['live_info'][0]['live_difficulty_id'])
    if 'live_info' in res:
        sql1 = """
        INSERT INTO `llproxy`.`score_match` (`uid`, `status`, `event_id`, `event_battle_room_id`, `event_rank`, `total_event_point`, `added_event_point`, `unit_id`, `display_rank`,
         `setting_award_id`, `live_difficulty_id`, `live_setting_id`,`use_quad_point`, `is_random`, `dangerous`,`update_time`)
    VALUES ('{}', '{}', '{}', '{}', '{}','{}', '{}', '{}', '{}', '{}', '{}', {},{}, {}, {},{});
        """.format(event_id, uid, 0, event_id, room_id, event_rank, total_event_point, 0, unit_id, display_rank,
                   setting_award_id, res['live_info'][0]['live_difficulty_id'], setting_id,
                   res['live_info'][0]['use_quad_point'],
                   res['live_info'][0]['is_random'], res['live_info'][0]['dangerous'], timestamp())
        sql.append(sql1)

        sql2 = """
        REPLACE INTO `llproxy`.`score_match_rooms` (`event_id`, `update_time`, `event_battle_room_id`, `status`, `players`, `matching_user`, `live_difficulty_id`, `live_setting_id`,
        `use_quad_point`, `is_random`, `dangerous`)
         VALUES ('{}', '{}', '{}', '0', '{}', '{}', '{}',{}, {}, {}, {});
        """.format(event_id, event_id, timestamp(), room_id, ','.join(playes),
                   escape_string(json.dumps(res['matching_user'], separators=(',', ':'), ensure_ascii=False)),
                   res['live_info'][
                                      0]['live_difficulty_id'], setting_id, res['live_info'][0]['use_quad_point'],
                   res['live_info'][0]['is_random'], res['live_info'][0]['dangerous'])
        sql.append(sql2)
    else:
        sql2 = """
                UPDATE `llproxy`.`score_match_rooms` SET `event_id`='{}', `update_time`='{}', `status`='0',`players`='{}',  `matching_user`='{}' WHERE  event_battle_room_id ='{}'
                """.format(event_id, event_id, timestamp(), ','.join(playes),
                           escape_string(json.dumps(res['matching_user'], separators=(',', ':'), ensure_ascii=False)),
                           room_id)
        sql.append(sql2)
    return sql


def score_match_status_1(uid, event_id, room_id, res):
    sql1 = "UPDATE `llproxy`.`score_match` SET `status` = '1',`update_time`={} WHERE uid = {} AND event_battle_room_id ={};".format(
        event_id, timestamp(), uid, room_id)
    sql2 = "UPDATE `llproxy`.`score_match_rooms` SET `status` = '1',`update_time`={} WHERE  event_battle_room_id ={};".format(
        event_id, timestamp(), room_id)
    return sql1, sql2


def pub_live_info(live_difficulty_id, merge_live_info):
    setting_id = get_setting_id(live_difficulty_id)
    json_str = json.dumps(merge_live_info, separators=(',', ':'))
    sql = """
    REPLACE INTO `llproxy`.`pub_live_info` (`live_difficulty_id`, `live_setting_id`,`update_time`, `is_random`, `dangerous`, `notes_speed`,  `merge_info_json`)
     VALUES ('{}',{}, '{}', {}, {}, {}, '{}')
    """.format(live_difficulty_id, setting_id, timestamp(), merge_live_info['live_info']['is_random'],
               merge_live_info['live_info']['dangerous'], merge_live_info['live_info']['notes_speed'],
               json_str)
    return sql,


def score_match_status_2(uid, event_id, room_id, req):
    sql1 = "UPDATE `llproxy`.`score_match` SET `status` = '2',`perfect_cnt` = '{}', `great_cnt` = '{}', `good_cnt` = '{}', `bad_cnt` = '{}', `love_cnt` = '{}', `miss_cnt` = '{}',`max_combo` = '{}',`score`= '{}',`update_time`={} WHERE uid = {} AND event_battle_room_id ={};".format(
        event_id, req['perfect_cnt'], req['great_cnt'], req['good_cnt'], req['bad_cnt'], req['love_cnt'],
        req['miss_cnt'], req['max_combo'], req['score_smile'] + req['score_cute'] + req['score_cool'],
        timestamp(), uid, room_id)
    sql2 = "UPDATE `llproxy`.`score_match_rooms` SET `status` = '2',`update_time`={} WHERE  event_battle_room_id ={};".format(
        event_id, timestamp(), room_id)
    return sql1, sql2


def score_match_status_3(uid, event_id, room_id, res):
    point_info = res['event_info']['event_point_info']
    sql1 = "UPDATE `llproxy`.`score_match` SET `status` = '3',`total_event_point` = '{}', `added_event_point` = '{}',`update_time`={}  WHERE uid = {} AND event_battle_room_id ={};".format(
        event_id, point_info['after_total_event_point'], point_info['added_event_point'], timestamp(), uid,
        room_id)

    sql2 = """
        UPDATE `llproxy`.`score_match_rooms` SET `event_id`='{}', `update_time`='{}', `status`='3',  `matching_user`='{}' WHERE  event_battle_room_id ={}
        """.format(event_id, event_id, timestamp(),
                   escape_string(json.dumps(res['matching_user'], separators=(',', ':'), ensure_ascii=False)), room_id)

    return sql1, sql2


def live_play(source):
    sqln = []
    res = source['res_data']
    req = source['req_data']
    uid = source['user_id']
    live_info = (res['live_info'][0]['live_difficulty_id'],
                 res['live_info'][0]['is_random'],
                 res['live_info'][0]['dangerous'],
                 res['live_info'][0]['use_quad_point']
                 )
    setting_id = get_setting_id(live_info[0])
    notes_info = (req['perfect_cnt'],
                  req['great_cnt'],
                  req['good_cnt'],
                  req['bad_cnt'],
                  req['miss_cnt'],
                  req['max_combo']
                  )
    score_info = (
        req['score_smile'] + req['score_cute'] + req['score_cool'],
        req['love_cnt']
    )
    event_info = [req['event_id'], req['event_point']]
    if event_info[0] is None:
        event_info[0] = 'NULL'
    elif 'event_info' in res:
        item_ids = []
        add_types = []
        amounts = []
        for reward in res['event_info']['event_reward_info']:
            if 'item_id' in reward:
                item_ids.append(str(reward['item_id']))
            else:
                item_ids.append('')
            add_types.append(str(reward['add_type']))
            amounts.append(str(reward['amount']))
        eventIFO = [res['event_info']['event_id'], res['event_info']['event_point_info']['after_event_point'],
                    res['event_info']['event_point_info']['after_total_event_point'],
                    res['event_info']['event_point_info']['added_event_point']]
        if req['event_point'] == 0:
            iseventsong = 1
        else:
            iseventsong = 0

        sqle = """
            INSERT INTO `llproxy`.`event_traditional` (`id`, `update_time`, `uid`,`live_setting_id`, `live_difficulty_id`, `is_random`, `dangerous`,`use_quad_point`, `score`, 
            `perfect_cnt`, `great_cnt`, `good_cnt`, `bad_cnt`, `miss_cnt`, `max_combo`, `love_cnt`, `no_judge_card`, `event_id`, `event_point`,
            `total_event_point`,`added_event_point`,`event_rewards_item_id`,`event_rewards_add_type`,`event_rewards_amount`,`is_event_song`)
             VALUES (NULL, '{}', '{}', {},'{}', {}, {}, {},'{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', NULL, {}, '{}', '{}', '{}', '{}', '{}', '{}',{})
            """.format(timestamp(), uid, setting_id, live_info[0], live_info[1], live_info[2], live_info[3],
                       score_info[0],
                       notes_info[0], notes_info[1], notes_info[2], notes_info[3], notes_info[4], notes_info[5],
                       score_info[1], eventIFO[0], eventIFO[1],
                       eventIFO[2], eventIFO[3], ','.join(item_ids), ','.join(add_types), ','.join(amounts),
                       iseventsong
                       )
        sqln.append(sqle)

    sql = """
    INSERT INTO `llproxy`.`live` (`id`, `update_time`, `uid`,`live_setting_id`, `live_difficulty_id`, `is_random`, `dangerous`,`use_quad_point`, `score`, 
    `perfect_cnt`, `great_cnt`, `good_cnt`, `bad_cnt`, `miss_cnt`, `max_combo`, `love_cnt`, `no_judge_card`, `event_id`, `event_point`)
     VALUES (NULL, '{}', '{}',{}, '{}', {}, {}, {},'{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', NULL, {}, '{}')
    """.format(timestamp(), uid, setting_id, live_info[0], live_info[1], live_info[2], live_info[3],
               score_info[0],
               notes_info[0], notes_info[1], notes_info[2], notes_info[3], notes_info[4], notes_info[5], score_info[1],
               event_info[0], event_info[1])
    sqln.append(sql)

    return sqln


def deck_info(source, notbyApi=False):
    uid = source['user_id']

    if notbyApi is False:
        res = source['res_data']['result']
    else:
        res = source['req_data']['unit_deck_list']
        for k in range(0, len(res)):
            res[k]['unit_owning_user_ids'] = res[k]['unit_deck_detail']
            del res[k]['unit_deck_detail']

    sql = """
            INSERT INTO `llproxy`.`deck_and_removable_Info` (`uid`, `update_time`, `deck_info`, `removable_info`) 
            VALUES ('{}', '{}', '{}', NULL)
            ON DUPLICATE KEY UPDATE `deck_info`=VALUES(deck_info),update_time=VALUES(update_time);
            """.format(uid, timestamp(), escape_string(json.dumps(res, separators=(',', ':'), ensure_ascii=False)))

    return sql,


def removeable_skill_info(source):
    sqln = []
    uid = source['user_id']
    res = source['res_data']['result']
    sql = """
                INSERT INTO `llproxy`.`deck_and_removable_Info` (`uid`, `update_time`, `deck_info`, `removable_info`) 
                VALUES ('{}', '{}', NULL, '{}')
                ON DUPLICATE KEY UPDATE `removable_info`=VALUES(removable_info),update_time=VALUES(update_time);
                """.format(uid, timestamp(),
                           escape_string(json.dumps(res, separators=(',', ':'), ensure_ascii=False)))
    sqln.append(sql)
    for k, v in res['equipment_info'].items():
        detail = []
        for x in v['detail']:
            detail.append(str(x['unit_removable_skill_id']))
        sqli = """
        UPDATE `llproxy`.`unit_unitAll` SET `unit_removable_skill_id` = '{}' WHERE `unit_unitAll`.`unit_owning_user_id` = {} 
        """.format(','.join(detail), v['unit_owning_user_id'])
        sqln.append(sqli)

    return sqln


def secretbox(source):
    uid = source['user_id']
    res = source['res_data']
    boxifo = res['secret_box_info']
    is_support_member = 0
    cnt = [-99, 0, 0, 0, 0, 0]
    unit_ids = []
    rarity_ids = []
    count = 1
    if 'count' in source['req_data']:
        count = source['req_data']['count']
    for unit in res['secret_box_items']['unit']:
        cnt[unit['unit_rarity_id']] += 1
        unit_ids.append(str(unit['unit_id']))
        rarity_ids.append(str(unit['unit_rarity_id']))
        if unit['is_support_member']:
            is_support_member = 1
    if ('item_id' not in boxifo['cost']) or (boxifo['cost']['item_id'] is None):
        boxifo['cost']['item_id'] = 'NULL'

    sql = """
    INSERT INTO `llproxy`.`secretbox` (`uid`, `update_time`, `secret_box_page_id`, `secret_box_id`, `name`, `cost_item_id`, 
    `result_unit_ids`, `result_rarity_ids`,`n_cnt`, `r_cnt`, `sr_cnt`, `ssr_cnt`, `ur_cnt`, `is_support_member`, `multi_count`) 
    VALUES ('{}', '{}', '{}', '{}', '{}', {}, 
    '{}', '{}', '{}', '{}','{}', '{}', '{}', '{}','{}')
    """.format(uid, timestamp(), res['secret_box_page_id'], boxifo['secret_box_id'], boxifo['name'],
               boxifo['cost']['item_id'],
               ','.join(unit_ids), ','.join(rarity_ids), cnt[1], cnt[2], cnt[3], cnt[5], cnt[4], is_support_member,
               count)

    return sql,


def effort_point_box(uid, effort_point_array):
    sqln = []
    for box in effort_point_array:
        if len(box['rewards']) == 0:
            continue
        box_spec_id = box['live_effort_point_box_spec_id']
        capacity = box['capacity']
        item_ids = []
        add_types = []
        amounts = []
        for reward in box['rewards']:
            if 'item_id' in reward:
                item_ids.append(str(reward['item_id']))
            elif 'unit_id' in reward:
                item_ids.append(str(reward['unit_id']))
            else:
                item_ids.append('')
                open('log.txt', 'a').write(json.dumps(effort_point_array) + '\n\n')
            add_types.append(str(reward['add_type']))
            amounts.append(str(reward['amount']))
        sql = """INSERT INTO `llproxy`.`effort_point_box` 
              (`uid`, `update_time`, `box_spec_id`, `capacity`, `rewards_item_id`, `rewards_add_type`, `rewards_amount`)
              VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}')
              """.format(uid, timestamp(), box_spec_id, capacity, ','.join(item_ids),
                         ','.join(add_types), ','.join(amounts))
        sqln.append(sql)
    return sqln


def user_info(user_info_obj, user_id=None):
    u = user_info_obj
    if user_id is None:

        sql = """
        REPLACE INTO `llproxy`.`user_info` 
        (`user_id`, `name`, `level`, `exp`, `previous_exp`, `next_exp`, `game_coin`, `sns_coin`, `paid_sns_coin`, 
        `social_point`, `unit_max`, `energy_max`, `energy_full_time`, 
         `over_max_energy`, `friend_max`, `invite_code`, `insert_date`, `update_date`, `update_time`) 
        VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', 
        '{}','{}', '{}', '{}', 
        '{}', '{}', '{}', '{}', '{}', '{}')
        """.format(u['user_id'], escape_string(u['name']), u['level'], u['exp'], u['previous_exp'], u['next_exp'],
                   u['game_coin'],
                   u['sns_coin'], u['paid_sns_coin']
                   , u['social_point'], u['unit_max'], u['energy_max'], u['energy_full_time'],
                   u['over_max_energy'], u['friend_max'], u['invite_code'], u['insert_date'], u['update_date'],
                   timestamp())
    else:
        sql = """
        UPDATE `llproxy`.`user_info` set `level`='{}',`exp`='{}', `previous_exp`='{}', `next_exp`='{}', `game_coin`='{}', `sns_coin`='{}', 
        `social_point`='{}', `unit_max`='{}', `energy_max`='{}', `energy_full_time`='{}', 
         `over_max_energy`='{}', `friend_max`='{}',`update_time`='{}' WHERE user_id='{}'
        """.format(u['level'], u['exp'], u['previous_exp'], u['next_exp'], u['game_coin'], u['sns_coin']
                   , u['social_point'], u['unit_max'], u['energy_max'], u['energy_full_time']
                   , u['over_max_energy'], u['friend_max'], timestamp(), user_id)
    # print(sql)
    return sql,


def user_navi(navi_info_dict):
    i = navi_info_dict
    sql = """
            UPDATE `llproxy`.`user_info` set `navi_owning_id`={},update_time={} WHERE user_id='{}'
            """.format(i['unit_owning_user_id'], timestamp(), i['uid'])

    return sql,


def display_rank(info_dict):
    i = info_dict
    sql = """
    UPDATE `llproxy`.`unit_unitAll` set `display_rank` = {} ,`update_time`={} WHERE unit_owning_user_id ={}
    """.format(i['display_rank'], timestamp(), i['unit_owning_user_id'])

    return sql,


def challenge_user_rplc(info_dict):
    i = info_dict
    sql = """
    REPLACE INTO event_challenge_users (uid, event_id, curr_pair_id, curr_round, total_event_point, high_score, finalized, update_time)
    VALUES (
    '{}','{}','{}','{}','{}','{}',{},'{}'
    )
    """.format(i['uid'], i['event_id'], i['curr_pair_id'], i['curr_round'], i['total_event_point'], i['high_score'],
               i['finalized'], timestamp())
    return sql,


def challenge_pair_init(uid, event_id, pair_id):
    sql = """
    INSERT INTO `event_challenge_pairs` (`uid`,`event_id`,`pair_id`,`curr_round`,`finalized`,`update_time`)
    VALUES ('{}','{}','{}','0','0','{}')
    """.format(uid, event_id, pair_id, timestamp())
    return sql,


def challenge_proceed(s_proceed, s_check, pair_id, round_n, finalized):
    sqln = []
    if s_proceed:
        challenge_items = json.dumps(s_proceed['req_data']['event_challenge_item_ids'])
    else:
        challenge_items = '[]'
    req = s_check['req_data']
    res = s_check['res_data']
    try:
        setid = live_setting_id[req['live_difficulty_id']]
    except KeyError:
        setid = 'NULL'
    chall_res = res['challenge_result']
    linf = chall_res['live_info'][0]
    lp = 0
    for mission in chall_res['mission_result']:
        if mission['bonus_type'] == 3050:
            lp += int(mission['bonus_param'])
    if finalized:
        sql = """
            update  `event_challenge_pairs` set `curr_round`='{}',finalized={},update_time='{}',round_setid_{}='{}',lp_add=lp_add+{}
            WHERE uid={} AND pair_id= {}
            """.format(round_n, finalized, timestamp(), round_n, setid, lp, s_check['user_id'], pair_id)
        sqln.append(sql)
    elif res['challenge_info']:
        reward_i = res['challenge_info']['accumulated_reward_info']
        rarity_l = [0, 0, 0, 0]
        for r in reward_i['reward_rarity_list']:
            rarity_l[r['rarity']] = r['amount']

        sql = """
            update  `event_challenge_pairs` set `curr_round`='{}',finalized={},player_exp='{}',game_coin='{}',
            event_point='{}',rarity_3_cnt='{}',rarity_2_cnt='{}',rarity_1_cnt='{}',update_time='{}',round_setid_{}={},
            lp_add=lp_add+{}
            WHERE uid={} AND pair_id= {}
            """.format(round_n, finalized, reward_i['player_exp'], reward_i['game_coin'], reward_i['event_point'],
                       rarity_l[3], rarity_l[2], rarity_l[1], timestamp(), round_n, setid,
                       lp, s_check['user_id'], pair_id)
        sqln.append(sql)

    sql2 = """
    INSERT INTO event_challenge (pair_id, round, update_time, uid, live_setting_id, live_difficulty_id, is_random, dangerous,
                             use_quad_point, score, perfect_cnt, great_cnt, good_cnt, bad_cnt, miss_cnt, max_combo, 
                             love_cnt, no_judge_card, event_id, event_point, rank, combo_rank, mission_result, 
                             reward_rarity_list, bonus_list,event_challenge_item_ids) 
    VALUES ('{}','{}','{}','{}',{},'{}',{},{},
    {},'{}','{}','{}','{}','{}','{}','{}',
    '{}',{},'{}','{}','{}','{}','{}',
    '{}','{}','{}'
    )""".format(pair_id, round_n, timestamp(), s_check['user_id'], setid, linf['live_difficulty_id'], linf['is_random'],
                linf['dangerous'], linf['use_quad_point'], req['score_smile'] + req['score_cute'] + req['score_cool'],
                req['perfect_cnt'], req['great_cnt'], req['good_cnt'], req['bad_cnt'], req['miss_cnt'],
                req['max_combo'], req['love_cnt'], 'NULL', req['event_id'], chall_res['reward_info']['event_point'],
                chall_res['rank'], chall_res['combo_rank'], escape_string(json.dumps(chall_res['mission_result'])),
                escape_string(json.dumps(chall_res['reward_info']['reward_rarity_list'])),
                escape_string(json.dumps(chall_res['bonus_list'])), escape_string(challenge_items)

                )
    sqln.append(sql2)
    return sqln


def challenge_finalize(source, pair_id):
    res = source['res_data']
    eventp = res['event_info']['event_point_info']
    rarity_l = [0, 0, 0, 0]
    ticket = 0
    for r in res['reward_item_list']:
        rarity_l[r['rarity']] += 1
        if r['add_type'] == 1000 and r['item_id'] == 1:
            ticket += r['amount']

    sql = """
    UPDATE event_challenge_pairs SET finalized=1,player_exp='{}',game_coin='{}',event_point='{}',after_event_point='{}',
    total_event_point='{}',added_event_point='{}',reward_item_list='{}',update_time='{}',rarity_3_cnt={},rarity_2_cnt={},rarity_1_cnt={},ticket_add={} WHERE uid = '{}' AND pair_id='{}'
    """.format(res['base_reward_info']['player_exp'], res['base_reward_info']['game_coin'],
               eventp['added_event_point'], eventp['after_event_point'], eventp['after_total_event_point'],
               eventp['added_event_point'], escape_string(json.dumps(res['reward_item_list'])), timestamp(),
               rarity_l[3], rarity_l[2], rarity_l[1],ticket,
               source['user_id'], pair_id
               )
    sql2 = """
    update `event_challenge_users` set finalized=1,total_event_point = '{}'
    """.format(eventp['after_total_event_point'])
    return sql, sql2


def timestamp():
    return int(time.time())


game_db_init()