PROJECT_NAME := enviroplussensorstomqtt
.PHONY: all venv install test clean install-service
all: install
venv:
	uv venv --allow-existing --system-site-packages --python /usr/bin/python3
install: venv
	uv pip install ruff
	uv pip install -e .[tests] --extra-index-url https://www.piwheels.org/simple/
test: install
	uv run ruff check .
	uv run pytest src/tests/
clean:
	rm -rf .venv
	rm -rf *.egg-info
	rm -rf dist build
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
install-service:
	@echo "Installing executable wrapper to /usr/local/bin/"
	@echo '#!/bin/bash' > /tmp/$(PROJECT_NAME)
	@echo 'exec $(CURDIR)/.venv/bin/$(PROJECT_NAME) "$$@"' >> /tmp/$(PROJECT_NAME)
	sudo cp /tmp/$(PROJECT_NAME) /usr/local/bin/$(PROJECT_NAME)
	sudo chmod +x /usr/local/bin/$(PROJECT_NAME)
	rm -f /tmp/$(PROJECT_NAME)
	@echo "Installing systemd service..."
	sudo cp systemd/$(PROJECT_NAME).service /etc/systemd/system/
	sudo systemctl daemon-reload
	@echo "Service installed successfully."
	@echo "Enable it with: sudo systemctl enable $(PROJECT_NAME)"
	@echo "Start it with: sudo systemctl start $(PROJECT_NAME)"
