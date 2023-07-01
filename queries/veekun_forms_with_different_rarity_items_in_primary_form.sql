-- to be run on the veekun database: fetches form/rarity combinations such that the form lacks a wild
-- held item of that rarity, but does have one of either the same rarity, or rarity 100, in its
-- "primary" form ("primary" = the one the others inherit their attributes from in reborn). This is
-- because the attribute inheritance might result in those forms incorrectly having an extra wild held
-- item.

with
	"sub100_rarities" ("percent") as ( select 1 union select 5 union select 50 ),
	"pokemon_items_ultra_sun" ("pokemon_id", "item_id", "rarity") as (
		select "pi"."pokemon_id", "pi"."item_id", "pi"."rarity"
		from "pokemon_items" as "pi"
		join "versions" as "v" on "v"."id" = "pi"."version_id" and "v"."identifier" = 'ultra-sun'
	)
select "pf"."identifier", "pi"."rarity", json_group_object("pf2"."identifier", "i"."identifier")
from "pokemon_forms" as "pf"
join "pokemon" as "p" on "p"."id" = "pf"."pokemon_id"
join "sub100_rarities" as "r" on not exists (
	select * from "pokemon_items_ultra_sun" as "pi" where "pi"."pokemon_id" = "p"."id" and "pi"."rarity" = "r"."percent"
)
join "pokemon_species" as "ps" on "ps"."id" = "p"."species_id"
join "pokemon" as "p2" on "p2"."species_id" = "ps"."id" and "p2"."id" != "p"."id"
join "pokemon_forms" as "pf2" on "pf2"."pokemon_id" = "p2"."id" and (
	-- we need it to be the reborn primary form (which the other forms will inherit their attributes from)
	-- this is sometimes different from the veekun form with order=1, i've manually added those exceptions
	("ps"."identifier" in ('pumpkaboo', 'gourgeist') and "pf2"."form_identifier" = 'super')
	or
	("ps"."identifier" = 'minior' and "pf2"."form_identifier" = 'red')
	or
	("ps"."identifier" not in ('pumpkaboo', 'gourgeist', 'minior') and "pf2"."form_order" = 1)
)
join "pokemon_items_ultra_sun" as "pi" on "pi"."pokemon_id" = "p2"."id" and (
	"pi"."rarity" = "r"."percent" or "pi"."rarity" = 100
)
join "items" as "i" on "i"."id" = "pi"."item_id"
where
	"pf"."is_battle_only" = 0
	-- exclude some forms not in reborn
	and not (
		("ps"."identifier" in ('pumpkaboo', 'gourgeist') and "pf"."form_identifier" in ('average', 'large'))
		or "ps"."identifier" = 'pikachu' and "pf"."form_identifier" is not null
	)
group by "pf"."id", "pi"."rarity"