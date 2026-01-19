.PHONY: setup activate run clean help

# Variables
VENV_DIR = venv
PYTHON = python3
PIP = $(VENV_DIR)/bin/pip
PYTHON_VENV = $(VENV_DIR)/bin/python
UVICORN = $(VENV_DIR)/bin/uvicorn
REQUIREMENTS = requirements.txt

# Colors for output
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[0;33m
NC = \033[0m # No Color

help:
	@echo "$(BLUE)Available commands:$(NC)"
	@echo "  $(GREEN)make setup$(NC)    - Create virtual environment and install requirements"
	@echo "  $(GREEN)make activate$(NC) - Show command to activate virtual environment"
	@echo "  $(GREEN)make run$(NC)      - Run the FastAPI application"
	@echo "  $(GREEN)make clean$(NC)    - Remove virtual environment"

setup:
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "$(GREEN)Virtual environment created!$(NC)"
	@echo "$(BLUE)Upgrading pip...$(NC)"
	$(PIP) install --upgrade pip
	@echo "$(BLUE)Installing requirements...$(NC)"
	$(PIP) install -r $(REQUIREMENTS)
	@echo "$(GREEN)✓ Setup complete!$(NC)"
	@echo "$(YELLOW)Run 'make activate' to see how to activate the environment$(NC)"

activate:
	@echo "$(YELLOW)To activate the virtual environment, run:$(NC)"
	@echo "$(GREEN)source $(VENV_DIR)/bin/activate$(NC)"
	@echo ""
	@echo "$(YELLOW)Or on Windows:$(NC)"
	@echo "$(GREEN)$(VENV_DIR)\\Scripts\\activate$(NC)"

run:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(YELLOW)Virtual environment not found. Running setup first...$(NC)"; \
		$(MAKE) setup; \
	fi
	@echo "$(BLUE)Starting FastAPI application...$(NC)"
	@echo "$(GREEN)Server will be available at: http://127.0.0.1:8001$(NC)"
	@echo "$(GREEN)API docs available at: http://127.0.0.1:8001/docs$(NC)"
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8001

clean:
	@echo "$(YELLOW)Removing virtual environment...$(NC)"
	rm -rf $(VENV_DIR)
	@echo "$(GREEN)✓ Cleanup complete!$(NC)"