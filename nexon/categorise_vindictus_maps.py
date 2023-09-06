import fnmatch
import json
import os

from bsp_tool import ValveBsp
from bsp_tool.branches import nexon


md = "E:/Mod/Vindictus/hfs/2022/maps"  # nexon.vindictus
# md69 = "E:/Mod/Vindictus/Client v1.69 EU/hfs/maps"  # nexon.vindictus69
# copied from megatest.log:
# errors = {"sprpv6": "Early end of lump! possiblesizeof=60.0 (is 64)"}
maps = {"01_boss.bsp", "01_boss_new.bsp", "01_mboss.bsp", "01_mboss_new.bsp",
        "01c_new.bsp", "01e_new.bsp", "01f_new.bsp", "01g_new.bsp", "01j.bsp",
        "01xe.bsp", "02_boss.bsp", "02_mboss_cut.bsp", "02c.bsp", "02d.bsp",
        "02i.bsp", "02j.bsp", "02k.bsp", "03_mboss_alice.bsp", "03e.bsp",
        "03f.bsp", "03j.bsp", "04b.bsp", "04e.bsp", "04f.bsp", "05_mboss.bsp",
        "05e.bsp", "05f.bsp", "05g.bsp", "05l.bsp", "06_boss.bsp", "06d.bsp",
        "06f.bsp", "06h.bsp", "06i.bsp", "06j.bsp", "07_boss.bsp",
        "07_mboss.bsp", "07a_new.bsp", "07b_new.bsp", "07c_new.bsp", "07d.bsp",
        "07d_new.bsp", "07e.bsp", "07e_new.bsp", "07f.bsp", "07f_new.bsp",
        "07g_new.bsp", "07h.bsp", "07i.bsp", "07i_new.bsp", "07j.bsp",
        "07j_new.bsp", "08_boss.bsp", "08_mboss.bsp", "08a.bsp", "08c.bsp",
        "08e.bsp", "08f.bsp", "08g.bsp", "08g_boss.bsp", "08h.bsp",
        "09_boss_special.bsp", "09_mboss.bsp", "09a.bsp", "09b.bsp",
        "09b_new.bsp", "09c.bsp", "09d.bsp", "10_boss.bsp", "11a.bsp",
        "11c.bsp", "11c_special.bsp", "11d.bsp", "12a_ds.bsp", "12b.bsp",
        "12b_ds.bsp", "12c.bsp", "12c_ds.bsp", "13_mboss.bsp",
        "13_mboss_farming.bsp", "13_mboss_new.bsp", "13a_farming.bsp",
        "13a_new.bsp", "13b_new.bsp", "13c_farming.bsp", "13c_new.bsp",
        "13d_farming.bsp", "13d_new.bsp", "13f_farming.bsp", "13f_new.bsp",
        "13g.bsp", "13g_farming.bsp", "13g_new.bsp", "13h_new.bsp",
        "14_boss.bsp", "14_boss_return.bsp", "14_mboss.bsp",
        "14_mboss_new.bsp", "14a_guild.bsp", "14a_new.bsp", "14b_guild.bsp",
        "14b_new.bsp", "14c_guild.bsp", "14c_new.bsp", "14d_guild.bsp",
        "14d_new.bsp", "14e_guild.bsp", "14e_new.bsp", "14f.bsp",
        "14f_guild.bsp", "14f_new.bsp", "14g.bsp", "14g_new.bsp",
        "15_boss.bsp", "15a_new.bsp", "15b_new.bsp", "15b_new_night.bsp",
        "15c_new.bsp", "15c_new_night.bsp", "15d_new.bsp",
        "15d_new_night.bsp", "15e_new.bsp", "15f_new_dusk.bsp",
        "15g_new_dusk.bsp", "15i_new.bsp", "15i_new_night.bsp",
        "15j_new_dusk.bsp", "15j_new_night.bsp", "15k_new.bsp",
        "15k_new_night.bsp", "15m.bsp", "15n.bsp", "16_boss_a.bsp",
        "16_boss_b.bsp", "16a_new.bsp", "16a_night.bsp", "16b_night.bsp",
        "16c_new.bsp", "16c_night.bsp", "16d_new_night.bsp", "16d_night.bsp",
        "16e_new.bsp", "16e_night.bsp", "16f.bsp", "16f_new.bsp",
        "16f_new_night.bsp", "16f_night.bsp", "16g_new_night.bsp",
        "16g_night.bsp", "16h_new.bsp", "16h_night.bsp", "16i_new.bsp",
        "16i_night.bsp", "16j_new.bsp", "16j_night.bsp", "16k_new_night.bsp",
        "16k_night.bsp", "16l_new_night.bsp", "16l_night.bsp", "16m_new.bsp",
        "16m_night.bsp", "16n_new.bsp", "16n_night.bsp", "16o_night.bsp",
        "16p.bsp", "17a.bsp", "17b.bsp", "17d.bsp", "3_02.bsp", "3_03.bsp",
        "3_04.bsp", "3_05_story.bsp", "3_06.bsp", "3_07.bsp", "3_08.bsp",
        "3_09.bsp", "3_10.bsp", "3_12.bsp", "3_13.bsp", "3_13_new.bsp",
        "3_14.bsp", "3_14_ex.bsp", "3_15.bsp", "3_16.bsp", "3_18.bsp",
        "3_19.bsp", "3_19_ex.bsp", "3_20a.bsp", "3_20b.bsp", "3_20c.bsp",
        "3_20d.bsp", "3_20e.bsp", "3_20f.bsp", "3_20g.bsp", "3_20h.bsp",
        "3_20k.bsp", "3_21.bsp", "3_22a.bsp", "3_22b.bsp", "3_22c.bsp",
        "3_22c_return.bsp", "3_22d.bsp", "3_22d_night.bsp", "3_22f.bsp",
        "3_22h.bsp", "3_22h_mboss.bsp", "3_23.bsp", "3_25.bsp",
        "3_25_ending.bsp", "3_25_screenshot.bsp", "3_26a_1.bsp", "3_26b.bsp",
        "3_26c.bsp", "3_26d.bsp", "3_26e.bsp", "3_26f.bsp", "3_26g_04.bsp",
        "3_26h.bsp", "3_26i.bsp", "3_26j.bsp", "3_26k.bsp", "3_26l.bsp",
        "3_26l_ds.bsp", "3_26l_ending.bsp", "3_27b.bsp", "3_29.bsp",
        "3_31.bsp", "3_game_start.bsp", "Storysector_talk.bsp",
        "bel_teaser.bsp", "bel_teaser_light.bsp", "create_character.bsp",
        "event_halloween_a.bsp", "event_halloween_b.bsp",
        "event_halloween_dream.bsp", "event_newyear_2014.bsp",
        "event_newyear_2015.bsp", "event_xmas14_b.bsp", "event_xmas_a.bsp",
        "event_xmas_b.bsp", "f01_cart_ex.bsp", "f01_start.bsp",
        "game_create_character.bsp", "game_create_character_arisha.bsp",
        "game_create_character_hagie.bsp", "game_create_character_lynn.bsp",
        "game_create_character_vin.bsp",
        "game_create_character_vin_arisha.bsp",
        "game_create_character_vin_hagie.bsp",
        "game_create_character_vin_lynn.bsp", "game_start.bsp",
        "game_start_neamhain_kalok.bsp", "game_start_vin.bsp", "h01.bsp",
        "h03.bsp", "h03_cut.bsp", "lobby_event.bsp", "lobby_fishingcraft.bsp",
        "lobby_fishingcraft_halloween.bsp", "lobby_fishingcraft_night.bsp",
        "lobby_fishingcraft_sunset.bsp", "lobby_fishingcraft_winter.bsp",
        "lobby_multiplayer.bsp", "lobby_multiplayer_berbe.bsp",
        "lobby_multiplayer_berbe_hall.bsp", "lobby_multiplayer_guild.bsp",
        "lobby_multiplayer_morvan.bsp", "lobby_multiplayer_morvan_s.bsp",
        "lobby_multiplayer_rochest.bsp", "lobby_multiplayer_rochest_s.bsp",
        "lobby_multiplayer_spring.bsp", "minigame.bsp", "minigame_wall.bsp",
        "nolwenn.bsp", "p03.bsp", "p04.bsp", "p05.bsp", "p06.bsp",
        "p06_blacklight.bsp", "p06_halloween.bsp", "p07.bsp",
        "pve_competition.bsp", "s3_00.bsp", "s3_game_start.bsp",
        "s3_lobby_multiplayer.bsp", "s3_lobby_multiplayer_rochest.bsp",
        "s3_lobby_multiplayer_rochest_w.bsp",
        "s3_lobby_multiplayer_winter.bsp", "sc_mini01.bsp",
        "sc_mini02.bsp", "sc_mini03.bsp", "start_2018_children_089b.bsp",
        "start_2018_foolsday_089b.bsp", "start_2018_spring_089b.bsp",
        "start_2018_summer_089b.bsp", "start_2020_lethor.bsp",
        "t05_school.bsp", "teaser_lethor.bsp",
        "w_boss.bsp", "w_boss02.bsp"}

# source.StaticPropv5
g0 = set()  # 35 maps
# vindictus69.StaticPropv6
g1 = maps.copy()  # 300 maps
# vindictus.StaticPropv6
g2 = set()  # 17 maps
# vindictus.StaticPropv7
g3 = set()  # 122 maps

maplist = fnmatch.filter(os.listdir(md), "*.bsp")
for map_name in filter(lambda m: m not in g1, maplist):
    bsp = ValveBsp(nexon.vindictus, os.path.join(md, map_name))
    assert len(bsp.GAME_LUMP.loading_errors) == 0, map_name
    v = bsp.GAME_LUMP.headers["sprp"].version
    if v == 5:  # source.StaticPropv5 (vindictus69.StaticPropv5)
        g0.add(map_name)
    # NOTE: g1 is also v6 (vindictus69.StaticPropv6)
    elif v == 6:  # vindictus.StaticPropv6
        g2.add(map_name)
    elif v == 7:
        g3.add(map_name)
    else:
        raise RuntimeError(f"v{v} StaticProp in {map_name}")

d = {"vindictus69.SPRPv5": sorted(g0), "vindictus69.SPRPv6": sorted(g1),
     "vindictus.SPRPv6": sorted(g2), "vindictus.SPRPv7": sorted(g3)}

with open("vindictus_maps.json", "w") as j:
    json.dump(d, j, indent=2)
