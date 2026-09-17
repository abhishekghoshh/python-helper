# Training Methods: Pre-training, Fine-tuning, Instruction Tuning, RLHF

## The Three Training Stages

Modern LLMs typically go through three stages:

```mermaid
flowchart LR
    PT[Pre-training] --> FT[Fine-tuning]
    FT --> RLHF[RLHF / Alignment]

    style PT fill:#3498db,color:#fff
    style FT fill:#e74c3c,color:#fff
    style RLHF fill:#27ae60,color:#fff
```

## 1. Pre-training

### What it is
Training a language model from scratch on a massive, general-purpose text corpus.

### The Data
The training data is typically a diverse mix of:
- Web pages (Common Crawl)
- Books and articles
- Wikipedia
- Source code (GitHub)
- Technical documentation

### The Process
```mermaid
flowchart LR
    TS["Token Sequences<br/>from massive text corpus"] --> Model["Neural Network Model<br/>(Transformer with billions of params)"]
    Model --> Pred["Predict next token"]
    Actual["Actual next token"] --> Compare["Compare prediction<br/>vs. actual (cross-entropy)"]
    Pred --> Compare
    Compare --> Loss["Compute loss"]
    Loss --> Grad["Backpropagation<br/>Compute gradients"]
    Grad --> Update["Adjust weights<br/>(gradient descent + AdamW)"]
    Update --> Model
    Model --> Repeat{"Repeat billions<br/>of iterations?"}
    Repeat -->|"Yes"| TS
    Repeat -->|"No"| Done["Model ready for inference<br/>or next training stage"]

    style TS fill:#3498db,color:#fff
    style Model fill:#e74c3c,color:#fff
    style Loss fill:#f39c12,color:#fff
    style Update fill:#27ae60,color:#fff
    style Done fill:#27ae60,color:#fff
```

### Characteristics

| Property | Value |
|----------|-------|
| **Data size** | Hundreds of GB to TB |
| **Compute** | Thousands of GPU days |
| **Cost** | Millions of dollars |
| **Output** | A general-purpose "base model" |

### Output Behavior
A pre-trained model can:
- Predict likely next words
- Write coherent text
- Answer simple questions

But it lacks:
- Following instructions well
- Being helpful, honest, and harmless
- Domain-specific knowledge

### Example
GPT-3 was pre-trained on 300 billion tokens from Common Crawl, web texts, and books.

## 2. Fine-tuning

### What it is
Starting from a pre-trained model and continuing training on a smaller,
domain-specific dataset.

### When to use it
- You need domain expertise (medical, legal, finance)
- You want the model to speak in a specific style
- You want better reasoning in a specific area

### Approaches

| Approach | Description | Data Needed |
|----------|-------------|-------------|
| **Full fine-tuning** | Update all model weights | Large, high-quality dataset |
| **LoRA** | Low-rank adaptation — train small adapter layers | Small dataset |
| **Prompt tuning** | Learn soft prompt tokens | Very small dataset |

#### LoRA (Low-Rank Adaptation)

```mermaid
flowchart LR
    subgraph "Original Layer"
        W["Weight matrix W<br/>(frozen)"]
    end
    subgraph "LoRA Adapters"
        A["A (down-projection)"]
        B["B (up-projection)"]
    end

    W --> Forward
    X["Input"] --> Forward
    A --> B
    B --> Add["+ (scaled)"]
    Forward --> Add
    Add --> Output

    style W fill:#bdc3c7,color:#333
    style A fill:#3498db,color:#fff
    style B fill:#3498db,color:#fff
```

Instead of updating the full weight matrix, LoRA adds:
- `W + (B × A) × scaling`
- A is a down-projection (rank r), B is an up-projection
- Only A and B are trained; W stays frozen
- Dramatically reduces memory and compute

### Fine-tuning vs. Training from Scratch

| Aspect | Fine-tuning | Training from Scratch |
|--------|------------|----------------------|
| **Cost** | Low (thousands of dollars) | High (millions) |
| **Data needed** | Small, specialized | Massive, general |
| **Risk** | Low | High (might fail to converge) |
| **Time** | Hours to days | Weeks to months |

## 3. Instruction Tuning

### What it is
Fine-tuning where the training data consists of **instruction-response pairs**:

```mermaid
graph TD
    IT["Instruction Tuning Process"]
    IT --> Ex1

    subgraph "Example 1: Summarization"
        direction TB
        I1["[INSTRUCTION]: Summarize this text in 3 bullet points:"]
        IN1["[INPUT]: Long article about climate change..."]
        OUT1["[RESPONSE]: • Rising temperatures are causing...<br/>• Coastal flooding threatens...<br/>• Carbon emissions must be reduced..."]
        I1 --> IN1 --> OUT1
    end

    subgraph "Example 2: Translation"
        direction TB
        I2["[INSTRUCTION]: Translate to French:"]
        IN2["[INPUT]: Hello, how are you?"]
        OUT2["[RESPONSE]: Bonjour, comment allez-vous ?"]
        I2 --> IN2 --> OUT2
    end

    subgraph "Example 3: Question Answering"
        direction TB
        I3["[INSTRUCTION]: Answer the following question:"]
        IN3["[INPUT]: What is the capital of France?"]
        OUT3["[RESPONSE]: The capital of France is Paris."]
        I3 --> IN3 --> OUT3
    end

    IT --> Ex1

    style IT fill:#27ae60,color:#fff
    style I1 fill:#3498db,color:#fff
    style OUT1 fill:#27ae60,color:#fff
    style I2 fill:#3498db,color:#fff
    style OUT2 fill:#27ae60,color:#fff
    style I3 fill:#3498db,color:#fff
    style OUT3 fill:#27ae60,color:#fff
```

### Purpose
Teaches the model to:
- Understand and follow instructions
- Respond in a helpful assistant style
- Adapt to user intent

### Example Datasets
- **FLAN** (Google): 1.8K tasks formatted as instructions
- **Self-Instruct**: Model-generated instruction-following data
- **Open Instruction Generalist**: 16K tasks across 61 types

## 4. RLHF (Reinforcement Learning from Human Feedback)

### Why RLHF?
Pre-trained and instruction-tuned models still:
- Can produce harmful or biased content
- May make up facts (hallucinate)
- Might not be helpful in the way humans want

RLHF aligns models with human values and preferences.

### The RLHF Pipeline

```mermaid
flowchart LR
    IT[Instruction-Tuned Model] --> Gen[Sample Responses]
    Gen --> Label[Labelers Rank Responses]
    Label --> RM[Train Reward Model]
    RM --> RL[Reinforcement Learning]
    RL --> FM[Final Model]

    style IT fill:#3498db,color:#fff
    style Label fill:#f39c12,color:#fff
    style RM fill:#e74c3c,color:#fff
    style RL fill:#27ae60,color:#fff
```

### Steps

1. **Generate responses**: The instruction-tuned model produces several
   responses to the same prompt
2. **Human labeling**: Human labelers rank responses from best to worst
3. **Train reward model**: A classifier learns to predict which response humans
   prefer
4. **RL fine-tuning**: Use the reward model as a reward function for PPO
   (Proximal Policy Optimization) to optimize the model

### PPO (Proximal Policy Optimization)

PPO is a reinforcement learning algorithm that:
- Maximizes expected reward (human preference)
- Avoids large policy updates (stays close to the original model)
- Balances exploration and exploitation

### What RLHF Achieves

- **Helpfulness**: Answers are more useful and relevant
- **Honesty**: Reduces hallucinations (somewhat)
- **Harmlessness**: Avoids dangerous/offensive content

### Limitations
- RLHF is expensive (requires lots of human labeling)
- It optimizes for average human preference, not truth
- Can introduce bias from labeler demographics
- May make the model less creative or overly cautious

## Comparison Table

| Method | Cost | Data | Purpose | Example |
|--------|------|------|---------|---------|
| **Pre-training** | $$$ | Massive general text | Build general model | GPT-3 |
| **Fine-tuning** | $$ | Small domain data | Domain adaptation | Med-PaLM |
| **Instruction tuning** | $ | Instruction-response | Follow instructions | FLAN-T5 |
| **RLHF** | $$ | Human rankings | Safety + helpfulness | ChatGPT, Claude |

## How This Connects to Our POC

Our POC uses models that have already gone through all three training stages:

- **OpenAI models** (gpt-3.5-turbo, gpt-4): Pre-trained → Instruction-tuned → RLHF
- **sentence-transformers** (all-MiniLM-L6-v2): Pre-trained → Fine-tuned on
  sentence pairs for semantic similarity

We use **prompting** (not more training) to adapt these models to our use case.
This is the practical reality for most developers.
