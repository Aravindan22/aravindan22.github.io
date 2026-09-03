from typing import TypedDict, Annotated, Literal, Union
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.postgres import PostgresStore
from langgraph.store.base import BaseStore
from pydantic import BaseModel
import logging
import os, sqlite3, sys
import psycopg
from uuid6 import uuid7
from langgraph.types import interrupt, Command

from utils.rich_print import print_rich_all_snapshots

from dotenv import load_dotenv
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, message):
        for stream in self.streams:
            stream.write(message)

    def flush(self):
        for stream in self.streams:
            stream.flush()

log_file = open("lorekeeper.log", "w", encoding="utf-8", buffering=1)
sys.stdout = TeeStream(sys.stdout, log_file)
sys.stderr = TeeStream(sys.stderr, log_file)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)
#region model 
from models.models import model
from models.settings import (
    HARDCODED_ADJUDICATION,
    HARDCODED_LORE,
    HARDCODED_NARRATIVE,
    HARDCODED_PERCEIVED_INTENT,
    USE_HARDCODED_RESPONSES,
)
#endregion

# 1. Define State
class LoreKeeperState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages] # Reducer handles appending
    current_scene: str
    player_intent: Literal["combat", "dialogue", "exploration", "out_of_bounds"]
    world_updates: list[str]
    npc_context: Union[dict,None]

class PerceiveActionOutputStructure(BaseModel):
    chosen_intent: str
class AdjudicateRulesOutputStructure(BaseModel):
    rule: str
class NarrateOutcomeOutputStructure(BaseModel):
    narrative: str
class SideLoadedOutputStructure(BaseModel):
    resp_lore: str



MASTER_MESSAGE = SystemMessage("You are in lorekeeper game acting as Game Master agent, Pick out the intent if needed, Narrate or Adjudicate rule when asked, available intents are: {}" \
"".format(["combat", "dialogue"]))

"""
Create the StateGraph skeleton. 
For the node functions, just have them return a dummy BaseMessage (e.g., AIMessage(content="Dummy response")) 
and a dummy player_intent so you can test the graph compilation.
"""
# 2. Define Nodes (Pseudo-code)
def perceive_action(state: LoreKeeperState):
    # Call Gemini to classify player input into player_intent
    # Return partial state update
    print("\n-== perceive_action ==-\n")
    if USE_HARDCODED_RESPONSES:
        chosen_intent = HARDCODED_PERCEIVED_INTENT
        logger.info("Using hardcoded perceived intent: %s", chosen_intent)
    else:
        structured_model = model.with_structured_output(PerceiveActionOutputStructure)
        msg__perceive_action = HumanMessage(content="Now Pick out a intent")
        resp = structured_model.invoke([*state['messages'], msg__perceive_action])
        print("Response ==-=== \n")
        print(resp)
        chosen_intent = resp.chosen_intent
        logger.info("Generated perceived intent: %s", chosen_intent)
    return {"messages": AIMessage(chosen_intent), 'player_intent':chosen_intent}

def manage_npc_memory(state: LoreKeeperState, *, store: BaseStore):
    npc_context = state.get('npc_context', None)
    graph_namespace = ("lorekeeper","npc")
    npc = "SideWalker"
    logger.info("Inside manage_npc_memory ==-===")
    if npc_context:
        npc_context = {'status':"dead"}
        store.put(graph_namespace, key=npc, value=npc_context)
    else:
        logger.info("Store has already NPC entry")
        npc_context = store.get(graph_namespace, key=npc)
    return {"npc_context":npc_context}

def adjudicate_rules(state: LoreKeeperState):
    print("\n-== adjudicating ==-\n")
    if USE_HARDCODED_RESPONSES:
        resp_text = HARDCODED_ADJUDICATION
        logger.info("Using hardcoded adjudication: %s", resp_text)
    else:
        msg__adjudicate_rules = HumanMessage(content="Right now you are adjudicating based on the state and game rules. Please determine the outcome of the action.")
        structured_model = model.with_structured_output(AdjudicateRulesOutputStructure)
        resp = structured_model.invoke([*state["messages"], msg__adjudicate_rules])
        resp_text = resp.rule
        logger.info("Generated adjudication: %s", resp_text)
    print("Adjudication Response: ", resp_text)
    return {"messages": [AIMessage(content=resp_text)]}

def narrate_outcome(state: LoreKeeperState):
    # Call Gemini to weave the outcome into a narrative description
    print("\n-== narrating ==-\n")
    if USE_HARDCODED_RESPONSES:
        resp_text = HARDCODED_NARRATIVE
        logger.info("Using hardcoded narrative: %s", resp_text)
    else:
        msg__narrate_outcome = HumanMessage(content="Narrate the final outcome based on the state and adjudication.")
        structured_model = model.with_structured_output(NarrateOutcomeOutputStructure)
        resp = structured_model.invoke([*state["messages"], msg__narrate_outcome])
        resp_text = resp.narrative
        logger.info("Generated narrative: %s", resp_text)
    print("Narrative Response: ", resp_text)
    return {"messages": [AIMessage(content=resp_text)]}

def propose_lore_drop(state: LoreKeeperState):
    print("\n-== ADDING JUICY LORE ==-\n")
    if USE_HARDCODED_RESPONSES:
        resp_lore = HARDCODED_LORE
        logger.info("Using hardcoded lore before action interrupt: %s", resp_lore)
    else:
        sideLoading_lore_message = HumanMessage(content="Generate a lore after this...")
        structured_model = model.with_structured_output(SideLoadedOutputStructure)
        resp = structured_model.invoke([*state['messages'], sideLoading_lore_message])
        resp_lore = resp.resp_lore
        logger.info("Generated lore before action interrupt: %s", resp_lore)
    
    print("Juicy lore: ", resp_lore)

    user_action = interrupt("Pick a action combat or dialogue\n")
    print("\nChosen Action : {}\n".format(user_action))
    logger.info("Action selected after interrupt: %s", user_action)
    return {"messages": [AIMessage(content=resp_lore)],  'player_intent':user_action}

# 3. Build Graph
graph_builder = StateGraph(LoreKeeperState)

# Add Nodes
graph_builder.add_node("perceive_action", perceive_action)
graph_builder.add_node("adjudicate_rules", adjudicate_rules)
graph_builder.add_node("narrate_outcome", narrate_outcome)
graph_builder.add_node("propose_lore_drop", propose_lore_drop)
graph_builder.add_node("manage_npc_memory", manage_npc_memory)

# Add Edges
graph_builder.add_edge(START, "perceive_action")

# Conditional routing based on GM's classification
def route_intent(state: LoreKeeperState) -> str:
    if state["player_intent"] == "combat":
        return "adjudicate_rules"
    elif state["player_intent"] == "dialogue":
        return "narrate_outcome" # Skip rules for pure RP
    return END

graph_builder.add_conditional_edges("perceive_action", route_intent)
graph_builder.add_edge("adjudicate_rules", "manage_npc_memory")
graph_builder.add_edge("manage_npc_memory", "narrate_outcome")
graph_builder.add_edge("narrate_outcome", "propose_lore_drop")
graph_builder.add_edge("propose_lore_drop", END)
# graph_builder.add_conditional_edges("propose_lore_drop", route_intent)
# graph_builder.add_edge("adjudicate_rules", "manage_npc_memory")
# graph_builder.add_edge("manage_npc_memory", "narrate_outcome")
# graph_builder.add_edge("narrate_outcome", END)



#region memory and checkpointer config
# checkpointer = InMemorySaver()
id_v7 = uuid7() # Generate a time-sortable UUIDv7
thread_id = "thread_id__"+str(id_v7)

conn = sqlite3.connect("memory.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

pg_db_uri = os.environ['POSTGRES_DB']
# Open connection directly
conn = psycopg.connect(pg_db_uri, autocommit=True)

# Pass connection directly into PostgresStore
pg_store = PostgresStore(conn)
pg_store.setup()
pg_store.setup() # Skip after once, this will setup the table
graph_namespace = ("lorekeeper","npc")
thread_id = "thread_id__session__1"
# thread_id = "thread_id__01a039d2-8565-7698-970c-0c9c89c57f1c"

print(thread_id)

configuration = {"configurable":{"thread_id":  thread_id}}
#endregion

# Compile
lorekeeper_graph = graph_builder.compile(checkpointer=checkpointer, store=pg_store)
initial_state = {"messages": add_messages(MASTER_MESSAGE, HumanMessage(content="I opened the inventry room."))}
final_state = lorekeeper_graph.invoke(initial_state, config=configuration)


current_state = lorekeeper_graph.get_state(configuration)


#region Interput HITL
if current_state.next:
    interrupt_info = current_state.tasks[0].interrupts[0].value
    user_action = input(interrupt_info)
    resumed_state = lorekeeper_graph.invoke(Command(resume=user_action), config=configuration) 
#endregion

snapshots_history = lorekeeper_graph.get_state_history(configuration)
snapshots = list(snapshots_history)
# print(list(state))
print_rich_all_snapshots(snapshots)
#region Replaying
"""
Replaying


# state_after_recalling = lorekeeper_graph.invoke(final_state, config=configuration)
# print("\n==========")
# print(state_after_recalling)
# print("\n==========")


replaying_snapshot = None
for snapshot in snapshots:
    if snapshot.metadata['step'] == 1:
        replaying_snapshot = snapshot
        break

replayed_state = lorekeeper_graph.invoke(None, replaying_snapshot.config)
print("\n========== replayed_state  ==========")
print(replayed_state)
print("\n==========")
snapshots_history = lorekeeper_graph.get_state_history(configuration)
snapshots = list(snapshots_history)
# print(list(state))
print_rich_all_snapshots(snapshots)
"""
#endregion