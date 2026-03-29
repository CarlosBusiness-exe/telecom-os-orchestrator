# 🌊 VigoFlow: Intelligent ISP Operation Suite

**VigoFlow** is a specialized Backend-for-Frontend (BFF) orchestrator designed to solve real-world logistical bottlenecks for **CBNET**. It transforms raw CRM data from the **VIGO API** into geographic intelligence and real-time operational insights.



## 📌 The Evolution
What started as a simple geospatial script has evolved into a comprehensive utility suite:

* **Geospatial Intelligence (V1):** Automated generation of **KML** maps, allowing technicians to visualize all pending services in Google Earth/Maps instantly.
* **Support Dashboard (V2):** A real-time, high-concurrency dashboard built with **FastAPI** that filters and prioritizes support tickets (Radio, Fiber, and Rural) using high-performance Python list comprehensions.

## 💡 The Problem & Solution
**The Bottleneck:** Field technicians previously spent more time navigating and searching for client history than performing repairs. Manual routing was slow and prone to error.

**The Solution:** **VigoFlow** acts as an intelligent adapter. It aggregates fragmented data—technical notes, coordinates, and client status—serving it through a clean, unified interface.



## 🛠️ Tech Stack & Architecture
* **Core:** **FastAPI** (Asynchronous Python) for non-blocking I/O.
* **Data Handling:** **Pydantic** for strict data validation and **HTTPX** for robust API communication.
* **Geospatial:** **SimpleKML** for automated mapping.
* **Frontend:** Vanilla JS & **Tailwind CSS** for a lightweight, high-performance dashboard.
* **DevOps:** Fully containerized with **Docker** & **Docker Compose**.

## 🚀 Getting Started
This project is optimized for internal ISP environments.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/CarlBorba/NetOps-Hub.git
    ```
2.  **Environment Setup:**
    Configure your `.env` with `VIGO_BASE_URL`, `VIGO_LOGIN`, and `VIGO_SENHA`.
3.  **Deployment:**
    ```bash
    docker-compose up --build
    ```
4.  **Access:**
    * **Dashboard:** `http://localhost:8001`
    * **Map Creator:** `http://localhost:8001/maps`