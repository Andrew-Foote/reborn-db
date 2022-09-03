select json_object(
    'name', "type"."name" || ' ' || "trainer"."name" || case
        when count(*) over (partition by "type"."name", "trainer"."name") > 1
        then ' ' || row_number() over (partition by "type"."name", "trainer"."name") else ''
    end
    ,'sprite', base64("type"."battle_sprite")
)
from "trainer"
join "trainer_type" as "type" on "type"."id" = "trainer"."type"
order by "trainer"."pbs_order"