select
	"tp"."trainer_type", "tp"."trainer_name", "tp"."party_id"
	,"tpv"."trainer_id", "tp"."index", "pokemon"."name", "tpv"."evs", "tpv"."moves"
from  "trainer_pokemon" as "tp"
join "pokemon" on "pokemon"."id" = "tp"."pokemon"
join "trainer_pokemon_ev" as "tpe_atk" on
	"tpe_atk"."trainer_type" = "tp"."trainer_type"
	and "tpe_atk"."trainer_name" = "tp"."trainer_name"
	and "tpe_atk"."party_id" = "tp"."party_id"
	and "tpe_atk"."pokemon_index" = "tp"."index"
	and "tpe_atk"."stat" = 'SA'
join "trainer_v" as "tv" on
	"tv"."type" = "tp"."trainer_type"
	and "tv"."name" = "tp"."trainer_name"
	and "tv"."party" = "tp"."party_id"
join "trainer_pokemon_v" as "tpv" on
	"tpv"."trainer_id" = "tv"."id" and "tpv"."index" = "tp"."index"
where exists (
	select * from "trainer_pokemon_ev" as "tpe"
	where
		"tpe"."trainer_type" = "tp"."trainer_type"
		and "tpe"."trainer_name" = "tp"."trainer_name"
		and "tpe"."party_id" = "tp"."party_id"
		and "tpe"."pokemon_index" = "tp"."index"	
		and "tpe"."stat" != 'ATK'
		and "tpe"."value" < "tpe_atk"."value"
		and not ("tpe"."stat" = 'SPD' and "tpe"."value" = 0)
)
and not exists (
	select * from "trainer_pokemon_move" as "tpm"
	join "move" on "move"."id" = "tpm"."move" and "move"."damage_class" = 'Special'
	where
		"tpm"."trainer_type" = "tp"."trainer_type"
		and "tpm"."trainer_name" = "tp"."trainer_name"
		and "tpm"."party_id" = "tp"."party_id"
		and "tpm"."pokemon_index" = "tp"."index"		
)