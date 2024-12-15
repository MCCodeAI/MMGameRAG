# MMGameRAG

MMGameRAG is a multimodal Retrieval-Augmented Generation (RAG) system designed for game strategy support, with an emphasis on text-and-image-based responses. The project currently focuses on strategies for 'Black Myth: Wu Kong.'

Project repository: [https://github.com/MCCodeAI/MMGameRAG](https://github.com/MCCodeAI/MMGameRAG)

## Team Members

- Yin Li, 20489800
- Hongji Li, 50028868
- Ling Li, 50016504

## Project Structure

- `index.html`: The main entry point of the project. This file serves as the interface for the system and links all necessary resources for visualization and interaction.
- `main.js`: Contains JavaScript logic for dynamic interactions and visualizations, including user interface elements.
- `templates/`: Includes HTML templates used in the system.
  - `chat.html`: A template for the chatbot interface.
  - `index.html`: The project’s main entry point.
  - `mmgameragvis.html`: A template for visualizing game data.
  - `1212_2135_HOME_4_Class2.html`: A template for search data visualization, showcasing results and trends effectively.
- `dataset/`: Contains cleaned data from various search engines.
- `vectorstore/`: Manages embeddings and data storage for retrieval operations.
- `docs/`: Contains additional documentation and assets, such as walkthroughs and context embeddings.
- `userlib/`: Custom libraries for extended functionality.
- `log/`: Stores logs for debugging and performance tracking.

## Prerequisites

1. **Python Environment**: Ensure Python is installed with all required libraries.
2. **Live Server Extension (for HTML visualization)**: Use VS Code's **Live Server** for real-time updates and testing.

## How to Run the Project

1. Clone the repository to your local machine.
2. Navigate to the project directory in your terminal.
3. Launch the project:
   - Open `index.html` using Live Server in Visual Studio Code.

## Key Features

### Multimodal Q&A System

- Provides both text and image-based responses for comprehensive game strategies.
- Includes visualizations like maps and walkthrough diagrams.

### Interactive Visualizations

- Powered by D3.js, the system supports dynamic and user-interactive visualizations to explore game data efficiently.

### Search and Retrieval

- Utilizes a vectorstore backend for efficient data retrieval.
- Supports keyword-based search with context embeddings.

## Example Use Case

1. Open `index.html` to access the main interface.
2. Interact with the chatbot to ask questions about specific game strategies.
3. View dynamic visualizations in real-time, such as location-based hints or heatmaps for popular search keywords.

## Contact

For any questions or further information, please contact: yligt@connect.hkust-gz.edu.cn
