# 🛰️ Telecom OS Orchestrator: Solving Real-World Logistics Bottlenecks

A Python-based backend service designed to **automate** Internet Service Provider (ISP) field operations by transforming raw API data into actionable **geographic intelligence**.

## 📌 The Problem
Before this solution, the technical team at **CBNET** faced a significant **manual overhead**. Field technicians had to manually search for client locations and service order details within the CRM, leading to:

* **Inefficient Routing:** Technicians spent more time navigating than performing installations or repairs.
* **Data Fragmentation:** Crucial technical notes were scattered across different API endpoints.
* **Delayed Response:** Generating a comprehensive map for a whole city's daily tasks was nearly impossible in real-time.

## 💡 The Solution
I developed an automated **Orchestrator** that interfaces with the **VIGO API**. It aggregates client data, credentials, and technical history, then processes these into a **KML (Keyhole Markup Language)** format.

**The Result:** A single file that, when opened in Google Earth or Google Maps, provides a complete, interactive logistical map of all pending services.



## 🎥 Project Demo
Below is a demonstration of the orchestrator in action using fictional data to protect client privacy (LGPD compliance):
https://github.com/user-attachments/assets/05a291a3-b12e-4081-8b88-7cfab0ed2b98



## 🛠️ Tech Stack & Architecture
* **Backend:** FastAPI (Asynchronous Python) for high-concurrency API requests.
* **Infrastructure:** Docker & Docker Compose for environment parity between development and production.
* **API Client:** HTTPX for non-blocking I/O operations.
* **Data Processing:** SimpleKML for automated geospatial data generation.
* **Environment:** Python-dotenv for secure credential management.



## 🚀 How to Run (Docker)
This project is fully containerized. To run it locally:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/CarlBorba/telecom-os-orchestrator.git](https://github.com/CarlBorba/telecom-os-orchestrator.git)
    ```

2. **Configure Environment:** 
    Create a .env file with your VIGO_BASE_URL and TOKEN.

3. **Launch with Docker:**
     ```bash
    docker-compose up --build
      ```

4. **Access:** 
    Open http://localhost:8000 in your browser.
