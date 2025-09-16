"""
Canvas Application Specific Tools

This package provides comprehensive Canvas LMS integration tools including:
- Canvas REST API client with full functionality
- Preprocessing pipelines for course setup
- Evaluation tools for task validation
- Command-line management tools

Based on the implementation from tasks/prepare/canvas-notification-python/
"""

from .api_client import (
    CanvasAPI,
    CanvasCourseManager,
    CanvasAssignmentManager,
    CanvasTokenManager,
    CourseInitializer,
    # Backward compatibility
    CanvasAPIClient
)

from .announcement_manager import AnnouncementManager
from .quiz_manager import QuizManager

from .preprocess_pipeline import (
    CanvasPreprocessUtils,
    create_canvas_utils,
    # Backward compatibility
    CanvasPreprocessPipeline,
    CanvasNotificationPreprocessPipeline,
    CanvasPreprocessPipelineBase
)

from .evaluator import (
    CanvasEvaluationUtils,
    create_canvas_evaluator,
    CanvasEvaluator,
    CanvasNotificationEvaluator,
    run_canvas_notification_evaluation,
    # Backward compatibility
    CanvasEvaluatorBase,
    run_basic_canvas_evaluation
)

# Import management tools
try:
    from . import tools
    _has_tools = True
except ImportError:
    _has_tools = False

__all__ = [
    # Core API classes
    'CanvasAPI',
    'CanvasCourseManager',
    'CanvasAssignmentManager',
    'CanvasTokenManager',
    'CourseInitializer',

    # New managers
    'AnnouncementManager',
    'QuizManager',

    # Preprocessing utilities
    'CanvasPreprocessUtils',
    'create_canvas_utils',

    # Evaluation classes
    'CanvasEvaluationUtils',
    'create_canvas_evaluator',
    'CanvasEvaluator',
    'CanvasNotificationEvaluator',
    'run_canvas_notification_evaluation',

    # Management tools (if available)
    'tools' if _has_tools else None,

    # Backward compatibility aliases
    'CanvasAPIClient',
    'CanvasPreprocessPipeline',
    'CanvasNotificationPreprocessPipeline',
    'CanvasPreprocessPipelineBase',
    'CanvasEvaluatorBase',
    'run_basic_canvas_evaluation'
]

# Remove None values from __all__
__all__ = [item for item in __all__ if item is not None]

# Version information
__version__ = "1.0.0"
__author__ = "MCPBench Canvas Module"