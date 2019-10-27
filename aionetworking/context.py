from __future__ import annotations
import contextvars


context_cv: contextvars.ContextVar = contextvars.ContextVar('context_cv', default={})