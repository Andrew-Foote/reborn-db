select json_object(
    'name', "move"."name"
    ,'damage_class', "move"."damage_class"
    ,'type', "move"."type"
    ,'power', "move"."power"
    ,'accuracy', "move"."accuracy"
    ,'pp', "move"."pp"
    ,'target', "target"."desc"
    ,'priority', "move"."priority"
    ,'function', "function"."desc"
    ,'additional_effect_chance', "move"."additional_effect_chance"
    ,'desc', "move"."desc"
)
from "move"
join "type" on "type"."id" = "move"."type"
join "move_target" as "target" on "target"."code" = "move"."target"
join "move_function" as "function" on "function"."code" = "move"."function"
order by "move"."code"