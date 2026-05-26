from pydantic import BaseModel
from typing import List, Dict, Any


class FeatureModel(BaseModel):
    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    story_points: int


class StoryModel(BaseModel):
    id: str
    feature_id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    story_points: int
    type: str = "development"


class TestingStoryModel(BaseModel):
    id: str
    related_story_id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    story_points: int


class HLDDPayload(BaseModel):
    title: str
    summary: str
    functional_requirements: List[str]
    project_management_tool: str
    technology_stack: List[str]
    acceptance_criteria: List[str]
    architecture_notes: List[str]
    architecture_diagram: Dict[str, Any]
    project_structure: List[str]
    features: List[FeatureModel]
    stories: List[StoryModel]
    testing_stories: List[TestingStoryModel]
