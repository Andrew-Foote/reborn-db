select json_object(
		'id', "move"."id"
    ,'name', "move"."name"
    ,'damage_class', "move"."damage_class"
    ,'type', "move"."type"
    ,'power', "move"."power"
    ,'accuracy', "move"."accuracy"
    ,'pp', "move"."pp"
    ,'desc', "move"."desc"
)
from "move"
order by "move"."code"