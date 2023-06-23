select
	"tp"."trainer_type", "tp"."trainer_name", "tp"."party_id"
	,"tpv"."trainer_id", "tp"."index", "pokemon"."name", "tpv"."nature", "tpv"."moves"
from  "trainer_pokemon" as "tp"
join "pokemon" on "pokemon"."id" = "tp"."pokemon"
join "trainer_v" as "tv" on
	"tv"."type_id" = "tp"."trainer_type"
	and "tv"."trainer_name" = "tp"."trainer_name"
	and "tv"."party_id" = "tp"."party_id"
join "trainer_pokemon_v" as "tpv" on
	"tpv"."trainer_id" = "tv"."id" and "tpv"."index" = "tp"."index"
join "nature" on "nature"."name" = "tpv"."nature"
where "nature"."increased_stat" = 'ATK' and "nature"."decreased_stat" != 'ATK'
and not exists (
	select * from "trainer_pokemon_move" as "tpm"
	join "move" on "move"."id" = "tpm"."move" and "move"."damage_class" = 'Physical'
	where
		"tpm"."trainer_type" = "tp"."trainer_type"
		and "tpm"."trainer_name" = "tp"."trainer_name"
		and "tpm"."party_id" = "tp"."party_id"
		and "tpm"."pokemon_index" = "tp"."index"		
)