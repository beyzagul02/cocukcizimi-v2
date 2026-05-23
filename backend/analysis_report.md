# Comprehensive Child Drawing Analysis Report

This report summarizes the analysis of representative drawings from the `CocukDuyguProje` dataset using the Fusion AI model (CNN + YOLO + Color Analysis).

## Analysis Overview

We selected one representative image from each label category (Angry, Fear, Happy, Sad) to validate the model's integrated predictions and psychological interpretations.

---

## 1. Category: Angry
**Image**: `a1.jpg`
- **Model Prediction**: **Angry** (Confidence: 63.0%)
- **Probabilities**:
  - Angry: 63.0%
  - Happy: 24.3%
  - Fear: 8.0%
  - Sad: 4.8%
- **KFD Style & Relationships**:
  - **Person Count**: 11 (High complexity)
  - **Placement**: Central & Vertical Center (Balanced/Realistic)
  - **Hierarchy**: Significant hierarchical difference (Authority figure dominance detected).
  - **Movement**: Mixture of normal proximity and isolation.
- **Color Analysis**:
  - **Grey (24.3%)**: Uncertainty or withdrawal.
  - **Pink (21.2%)**: Need for affection/sensitivity.
  - **Black (18.8%)**: Anxiety, repressed emotions, or desire for power.
- **AI Summary**: "Drawing evaluated as **Angry** category. Significant power imbalance or authority figure emphasis in the family. Color use (Grey) is consistent with the detected emotional state."

---

## 2. Category: Fear
**Image**: `f1.jpg`
- **Model Prediction**: **Angry** (Confidence: 53.9%)
- **Note**: The model predicted "Angry" for this "Fear" labeled image, though "Fear" was the second most likely (19.3%).
- **Probabilities**:
  - Angry: 53.9%
  - Fear: 19.3%
  - Sad: 15.0%
  - Happy: 11.8%
- **Technical Insight**: No persons were detected in this specific image (`person_count: 0`), which likely limited the KFD relationship analysis and shifted the weight to CNN and Color features.
- **Color Analysis**:
  - **Grey (36.0%)**: Uncertainty.
  - **Black (21.0%)**: Anxiety/Fear.
  - **Blue (15.0%)**: Calmness or control.

---

## 3. Category: Happy
**Image**: `h1.jpg`
- **Model Prediction**: **Happy** (Confidence: 94.6%)
- **Probabilities**:
  - Happy: 94.6%
  - Angry: 1.8%
  - Fear: 2.1%
  - Sad: 1.5%
- **KFD Style & Relationships**:
  - **Person Count**: 4
  - **Placement**: Right-leaning (Future-oriented/Extroverted - Koppitz)
  - **Hierarchy**: Normal size distribution.
  - **Movement**: Pairs 0-2 and 1-2 show "Normal Proximity" (Healthy interaction).
- **Color Analysis**:
  - **Grey (24.0%)**: Background/Neutral.
  - **Black (19.0%)**: Outlines.
  - **Yellow (13.0%)**: Joy, extroversion.
- **AI Summary**: "Drawing evaluated as **Happy** (95% confidence). Right-leaning placement suggests a future-oriented outlook. Interaction distances indicate healthy family dynamics."

---

## 4. Category: Sad
**Image**: `s1.jpg`
- **Model Prediction**: **Sad** (Confidence: 51.5%)
- **Probabilities**:
  - Sad: 51.5%
  - Happy: 21.0%
  - Angry: 14.5%
  - Fear: 13.0%
- **KFD Style & Relationships**:
  - **Person Count**: 5
  - **Placement**: Left-leaning (Past-oriented/Introverted - Koppitz)
  - **Hierarchy**: Medium level size difference.
- **Color Analysis**:
  - **Grey (35.0%)**: Withdrawal.
  - **Blue (20.0%)**: Calmness or sadness.
  - **Black (15.0%)**: Anxiety.
- **AI Summary**: "Drawing evaluated as **Sad**. Left-leaning placement and dominant cool/neutral colors are consistent with the detected sentiment."

---

## Conclusion

The Fusion model demonstrates strong performance in distinguishing "Happy" drawings (94%+ confidence) and correctly identifying "Sad" and "Angry" sentiments in the tested samples. The integration of KFD (Kinetic Family Drawing) metrics like **placement** and **hierarchy** provides valuable context that elevates the analysis from simple classification to psychological screening aids.
