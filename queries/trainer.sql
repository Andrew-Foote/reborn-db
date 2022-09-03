select "tp"."pokemon", "tp"."form", "tp"."level", "i"."name", "a"."name" as "ability", "tp"."nature", "tp"."ivs",
"hp"."value" as "hp_ev" , "atk"."value" as "atk_ev", "def"."value" as "def_ev", "spd"."value" as "spd_ev",
"sa"."value" as "sa_ev", "sd"."value" as "sd_ev", "mv1"."name" as "move1", "mv2"."name" as "move2", "mv3"."name" as "move3", "mv4"."name" as "move4",
"mv1"."pp", "mv2"."pp", "mv3"."pp", "mv4"."pp"
from  "trainer_pokemon" as "tp"
left join "item" as "i" on "i"."id" = "tp"."item"
join "pokemon_ability" as "pa" on "pa"."pokemon" = "tp"."pokemon" and "pa"."form" = "tp"."form" and "pa"."index" = "tp"."ability"
join "ability" as "a" on "a"."id" = "pa"."ability"
join "trainer_pokemon_ev" as "hp" on "hp"."trainer_type" = "tp"."trainer_type" and "hp"."trainer_name" = "tp"."trainer_name"
and "hp"."trainer_id" = "tp"."trainer_id" and "hp"."pokemon_index" = "tp"."index" and "hp"."stat" = 'HP'
join "trainer_pokemon_ev" as "atk" on "atk"."trainer_type" = "tp"."trainer_type" and "atk"."trainer_name" = "tp"."trainer_name"
and "atk"."trainer_id" = "tp"."trainer_id" and "atk"."pokemon_index" = "tp"."index" and "atk"."stat" = 'ATK'
join "trainer_pokemon_ev" as "def" on "def"."trainer_type" = "tp"."trainer_type" and "def"."trainer_name" = "tp"."trainer_name"
and "atk"."trainer_id" = "tp"."trainer_id" and "def"."pokemon_index" = "tp"."index" and "def"."stat" = 'DEF'
join "trainer_pokemon_ev" as "spd" on "spd"."trainer_type" = "tp"."trainer_type" and "spd"."trainer_name" = "tp"."trainer_name"
and "atk"."trainer_id" = "tp"."trainer_id" and "spd"."pokemon_index" = "tp"."index" and "spd"."stat" = 'SPD'
join "trainer_pokemon_ev" as "sa" on "sa"."trainer_type" = "tp"."trainer_type" and "sa"."trainer_name" = "tp"."trainer_name"
and "atk"."trainer_id" = "tp"."trainer_id" and "sa"."pokemon_index" = "tp"."index" and "sa"."stat" = 'SA'
join "trainer_pokemon_ev" as "sd" on "sd"."trainer_type" = "tp"."trainer_type" and "sd"."trainer_name" = "tp"."trainer_name"
and "sd"."trainer_id" = "tp"."trainer_id" and "sd"."pokemon_index" = "tp"."index" and "sd"."stat" = 'SD'

join "trainer_pokemon_move" as "m1" on "m1"."trainer_type" = "tp"."trainer_type" and "m1"."trainer_name" = "tp"."trainer_name"
and "m1"."trainer_id" = "tp"."trainer_id" and "m1"."pokemon_index" = "tp"."index" and "m1"."move_index" = 0
join "move" as "mv1" on "mv1"."id" = "m1"."move"

left join "trainer_pokemon_move" as "m2" on "m2"."trainer_type" = "tp"."trainer_type" and "m2"."trainer_name" = "tp"."trainer_name"
and "m2"."trainer_id" = "tp"."trainer_id" and "m2"."pokemon_index" = "tp"."index" and "m2"."move_index" = 1
left join "move" as "mv2" on "mv2"."id" = "m2"."move"

left join "trainer_pokemon_move" as "m3" on "m3"."trainer_type" = "tp"."trainer_type" and "m3"."trainer_name" = "tp"."trainer_name"
and "m1"."trainer_id" = "tp"."trainer_id" and "m3"."pokemon_index" = "tp"."index" and "m3"."move_index" = 2
left join "move" as "mv3" on "mv3"."id" = "m3"."move"

left join "trainer_pokemon_move" as "m4" on "m4"."trainer_type" = "tp"."trainer_type" and "m4"."trainer_name" = "tp"."trainer_name"
and "m4"."trainer_id" = "tp"."trainer_id" and "m4"."pokemon_index" = "tp"."index" and "m4"."move_index" = 3
left join "move" as "mv4" on "mv4"."id" = "m4"."move"

where "tp"."trainer_type" = 'REGIGIGAS' and "tp"."trainer_name" = 'Regigigas' and "tp"."trainer_id" = 0
order by "tp"."index"