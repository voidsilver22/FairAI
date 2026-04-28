import torch
import torch.nn as nn
from torch.autograd import Function

class GradientReversalLayer(Function):
    @staticmethod
    def forward(ctx, x, alpha):
        ctx.alpha = alpha
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output):
        output = grad_output.neg() * ctx.alpha
        return output, None

class FairLensDANN(nn.Module):
    def __init__(self, protected_columns, input_dim=384, hidden_dim=512):
        super(FairLensDANN, self).__init__()
        
        # --- A. The Feature Extractor ---
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU()
        )
        
        # --- B. The Score Predictor ---
        self.score_predictor = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid() 
        )
        
        # --- C. DYNAMIC ADVERSARIES (ModuleDict) ---
        self.adversaries = nn.ModuleDict()
        for col in protected_columns:
            self.adversaries[col] = nn.Sequential(
                nn.Linear(hidden_dim, 32),
                nn.ReLU(),
                nn.Linear(32, 1),
                nn.Sigmoid()
            )

    def forward(self, x, alpha=1.0):
        features = self.feature_extractor(x)
        predicted_score = self.score_predictor(features)
        reversed_features = GradientReversalLayer.apply(features, alpha)
        
        adv_predictions = {}
        for col, adversary in self.adversaries.items():
            adv_predictions[col] = adversary(reversed_features)
            
        return predicted_score, adv_predictions