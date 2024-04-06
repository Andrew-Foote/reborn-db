
with "cc_cmds" as (
	select
		"epc"."map_id",
		"epc"."event_id",
		"epc"."page_number",
		"epc"."command_number",
		"arg"."value",
		dense_rank() over "win" - "epc"."command_number" as "block_id"
		from "event_page_command" as "epc"
	join "event_command_text_argument" as "arg" on (
		"arg"."command" = "epc"."command" 
		and "arg"."command_type" = 'ContinueComment'
		and "arg"."command_subtype" = ''
		and "arg"."parameter" = 'text'
	)
	window "win" as (
		partition by "epc"."map_id", "epc"."event_id", "epc"."page_number"
		order by "epc"."command_number"
	)
	order by "epc"."map_id", "epc"."event_id", "epc"."page_number", "epc"."command_number"
),
"cc_cmds1" as (
	select
		"map_id", "event_id", "page_number", "block_id", "command_number", "value"
	from "cc_cmds"
	window "win" as (partition by "map_id", "event_id", "page_number", "block_id")
	order by "map_id", "event_id", "page_number", "command_number"
)
select * from "cc_cmds1"