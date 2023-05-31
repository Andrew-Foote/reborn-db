select json_object(
    'name', "type"."name" || ' ' || ifnull("trainer"."name", '[no name]') || case
        when count(*) over (partition by "type"."name", "trainer"."name") > 1
        then ' ' || row_number() over (partition by "type"."name", "trainer"."name") else ''
    end
    ,'sprite', base64("type"."battle_sprite")
)
from "battle_facility_trainer" as "trainer"
join "trainer_type" as "type" on "type"."id" = "trainer"."type"
order by "trainer"."list", "trainer"."index"