from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, add_messages
from pydantic import BaseModel
import os
from dotenv import load_dotenv
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
#region model 
from models.models import model
#endregion

# 1. Define State
class LoreKeeperState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages] # Reducer handles appending
    current_scene: str
    player_intent: Literal["combat", "dialogue", "exploration", "out_of_bounds"]
    world_updates: list[str]

class PerceiveActionOutputStructure(BaseModel):
    chosen_intent: str
class AdjudicateRulesOutputStructure(BaseModel):
    rule: str
class NarrateOutcomeOutputStructure(BaseModel):
    narrative: str



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
    structured_model = model.with_structured_output(PerceiveActionOutputStructure)
    msg__perceive_action = HumanMessage(content="Now Pick out a intent")    
    resp = structured_model.invoke([*state['messages'] ,msg__perceive_action])
    print("Response ==-=== \n")
    print(resp)
    chosen_intent = resp.chosen_intent
    return {"messages": AIMessage(chosen_intent), 'player_intent':chosen_intent}

def adjudicate_rules(state: LoreKeeperState):
    print("\n-== adjudicating ==-\n")
    msg__adjudicate_rules = HumanMessage(content="Right now you are adjudicating based on the state and game rules. Please determine the outcome of the action.")
    structured_model = model.with_structured_output(AdjudicateRulesOutputStructure)
    resp = structured_model.invoke([*state["messages"], msg__adjudicate_rules])
    resp_text = resp.rule
    print("Adjudication Response: ", resp_text)
    return {"messages": [AIMessage(content=resp_text)]}

def narrate_outcome(state: LoreKeeperState):
    # Call Gemini to weave the outcome into a narrative description
    print("\n-== narrating ==-\n")
    msg__narrate_outcome = HumanMessage(content="Narrate the final outcome based on the state and adjudication.")
    structured_model = model.with_structured_output(NarrateOutcomeOutputStructure)
    resp = structured_model.invoke([*state["messages"], msg__narrate_outcome])
    resp_text = resp.narrative
    print("Narrative Response: ", resp_text)
    return {"messages": [AIMessage(content=resp_text)]}

# 3. Build Graph
graph_builder = StateGraph(LoreKeeperState)

# Add Nodes
graph_builder.add_node("perceive_action", perceive_action)
graph_builder.add_node("adjudicate_rules", adjudicate_rules)
graph_builder.add_node("narrate_outcome", narrate_outcome)

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
graph_builder.add_edge("adjudicate_rules", "narrate_outcome")
graph_builder.add_edge("narrate_outcome", END)

# Compile
lorekeeper_graph = graph_builder.compile()
initial_state = {"messages": add_messages(MASTER_MESSAGE, HumanMessage(content="I opened the inventry room."))}
final_state = lorekeeper_graph.invoke(initial_state)

print(final_state["messages"])