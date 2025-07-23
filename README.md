# A1 Agentic System

Complete implementation of the A1 agentic system for autonomous smart contract exploit generation using Grok-4-0709, based on the research paper specifications.

## 🚀 Features

- **6 Domain-Specific Tools**: Source code fetcher, constructor parameter analyzer, blockchain state reader, code sanitizer, concrete execution, revenue normalizer
- **5-Iteration Feedback Loop** with diminishing returns and early termination
- **Autonomous Strategy Generation** with confidence scoring
- **Real Blockchain Integration** via Alchemy (Ethereum + BSC)
- **Economic Analysis** with USD profit calculations and gas estimation
- **Comprehensive Database Storage** with SQLite for results and metrics
- **Batch Processing** support for multiple contracts

## 📋 Prerequisites

- Python 3.8+
- Node.js (for Foundry/Forge)
- Git

## 🛠️ Installation

1. **Clone the repository:**
```bash
git clone https://github.com/Raroford32/a1.git
cd a1
```

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

3. **Install Foundry (for concrete execution):**
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

4. **Set up environment variables:**

Create a `.env` file in the project root with your API keys:
```env
XAI_API_KEY=your_xai_api_key_here
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/your_alchemy_api_key_here
BSC_RPC_URL=https://bnb-mainnet.g.alchemy.com/v2/your_alchemy_api_key_here
ETHERSCAN_API_KEY=your_etherscan_api_key_here
BSCSCAN_API_KEY=your_bscscan_api_key_here

GROK_MODEL=grok-4-0709
GROK_BASE_URL=https://api.x.ai/v1
MAX_ITERATIONS=5
RESULTS_DIR=./results
LOG_LEVEL=INFO
```

## 🎯 Usage

### Basic Usage

Run the A1 system on a list of target contracts:

```bash
python main.py --targets targets.txt
```

### Advanced Options

```bash
# Run with custom configuration
python main.py --targets targets.txt --max-iterations 3 --output-dir ./custom_results

# Run on a single contract
python main.py --contract 0x1234567890123456789012345678901234567890

# Run with verbose logging
python main.py --targets targets.txt --log-level DEBUG
```

### Target File Format

Create a `targets.txt` file with one contract address per line:
```
0x1234567890123456789012345678901234567890
0xabcdefabcdefabcdefabcdefabcdefabcdefabcd
```

### Simple Test

Run a quick test on the first few contracts:

```bash
python simple_test.py
```

### Check Results

View stored results in the database:

```bash
python check_results.py
```

## 📊 Output

The system generates:

- **Execution Results**: Stored in SQLite database (`a1_results.db`)
- **Detailed Analysis**: JSON files with exploit strategies and execution plans
- **Economic Metrics**: Profit potential calculations in USD
- **Logs**: Comprehensive logging in `a1_system.log`

## 🔧 Configuration

Key configuration options in `.env`:

- `MAX_ITERATIONS`: Maximum analysis iterations (default: 5)
- `GROK_MODEL`: Grok model to use (default: grok-4-0709)
- `LOG_LEVEL`: Logging verbosity (INFO, DEBUG, WARNING, ERROR)
- `RESULTS_DIR`: Directory for storing results (default: ./results)

## 🏗️ Architecture

### Core Components

- **A1Agent**: Main controller orchestrating the analysis workflow
- **ToolOrchestrator**: Manages the 6 domain-specific tools
- **FeedbackProcessor**: Handles iteration feedback and confidence scoring
- **StrategyGenerator**: Creates exploit strategies based on analysis

### Domain-Specific Tools

1. **Source Code Fetcher**: Retrieves and analyzes smart contract source code
2. **Constructor Parameter**: Analyzes deployment parameters and security implications
3. **Blockchain State Reader**: Captures comprehensive contract state snapshots
4. **Code Sanitizer**: Cleans and optimizes contract code for analysis
5. **Concrete Execution**: Simulates exploits using Foundry/Forge
6. **Revenue Normalizer**: Calculates economic profitability with real-time prices

## 🧪 Testing

Run the test suite:

```bash
python -m pytest tests/
```

Run specific test categories:

```bash
# Unit tests
python -m pytest tests/unit/

# Integration tests
python -m pytest tests/integration/

# End-to-end tests
python -m pytest tests/e2e/
```

## 📈 Performance

- **Processing Speed**: ~2-5 minutes per contract (depending on complexity)
- **Success Rate**: Varies by contract complexity and vulnerability presence
- **Resource Usage**: Moderate CPU/memory usage, network-dependent for RPC calls

## 🔒 Security

- API keys are stored in `.env` (never commit this file)
- All blockchain interactions are read-only during analysis
- Exploit simulations run in isolated Foundry environments

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Based on the A1 research paper for autonomous smart contract exploit generation
- Uses Grok-4-0709 for advanced language model capabilities
- Integrates with Foundry for concrete execution simulation

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the logs in `a1_system.log` for debugging information
- Ensure all API keys are properly configured in `.env`

---

**Link to Devin run**: https://app.devin.ai/sessions/7fbfe1bcec46435e81d3589b428cb542  
**Requested by**: @Raroford32
