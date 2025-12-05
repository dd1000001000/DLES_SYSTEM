import torch.nn as nn

class TransformerEncoder(nn.Module):
    """ Transformer Encoder Model """
    def __init__(self, input_dim=768, embed_dim=512, num_heads=4, num_layers=6):
        super().__init__()
        self.embedding = nn.Sequential(
            nn.Linear(input_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU()
        )
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=embed_dim * 4,
            activation='gelu',
            dropout=0.1,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.projector = nn.Linear(embed_dim, input_dim)  # 投影回原始维度

    def forward(self, x):
        x = self.embedding(x)
        x = self.transformer(x)
        x = self.projector(x)  # 投影回原始维度
        return x

class TableContrastiveModel(nn.Module):
    def __init__(self, input_dim=768, embed_dim=512, num_heads=4, num_layers=6):
        super(TableContrastiveModel, self).__init__()
        self.encoder = TransformerEncoder(input_dim, embed_dim, num_heads, num_layers)

    def forward(self, x):
        features = self.encoder(x)
        return features