import torch
import torch.nn as nn

# 论文：6 层 Transformer、8 个注意力头；输入输出都是 n×1024（取决于嵌入模型的维度，保存在检查点里）（n 为表格的列数）
DEFAULT_CONFIG = {
    'input_dim': 1024,
    'embed_dim': 512,
    'num_heads': 8,
    'num_layers': 6,
    'dropout': 0.1,
    # 在输入向量上加一条残差连接：模型只需要学习“列与列之间的上下文修正量”，
    # 不会因为 512 维的瓶颈把 嵌入向量本身的语义丢掉
    'residual': True,
}


class TransformerEncoder(nn.Module):
    """ Transformer Encoder Model：把相互独立的列向量变成带有同表其他列上下文的列向量 """
    def __init__(self, input_dim=1024, embed_dim=512, num_heads=8, num_layers=6, dropout=0.1, residual=True):
        super().__init__()
        self.residual = residual
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
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers, enable_nested_tensor=False)
        self.projector = nn.Linear(embed_dim, input_dim)  # 投影回原始维度

    def forward(self, x, padding_mask=None):
        """x: (n, 768) 或 (batch, n, 768)；padding_mask: (batch, n)，True 表示这一列是补齐出来的"""
        h = self.embedding(x)
        h = self.transformer(h, src_key_padding_mask=padding_mask)
        h = self.projector(h)  # 投影回原始维度
        return x + h if self.residual else h


class TableContrastiveModel(nn.Module):
    def __init__(self, input_dim=1024, embed_dim=512, num_heads=8, num_layers=6, dropout=0.1, residual=True):
        super(TableContrastiveModel, self).__init__()
        self.encoder = TransformerEncoder(input_dim, embed_dim, num_heads, num_layers, dropout, residual)

    def forward(self, x, padding_mask=None):
        return self.encoder(x, padding_mask)


def build_model(config: dict = None) -> TableContrastiveModel:
    return TableContrastiveModel(**{**DEFAULT_CONFIG, **(config or {})})


def save_checkpoint(model: TableContrastiveModel, config: dict, path: str, extra: dict = None):
    # 只保存权重和结构参数，不再 pickle 整个模型对象：加载时不会执行文件里的任意代码，也不依赖类的导入路径
    torch.save({'config': {**DEFAULT_CONFIG, **config}, 'state_dict': model.state_dict(), 'extra': extra or {}}, path)


def load_checkpoint(path: str, device='cpu') -> TableContrastiveModel:
    checkpoint = torch.load(path, map_location=device, weights_only=True)
    model = build_model(checkpoint['config'])
    model.load_state_dict(checkpoint['state_dict'])
    return model.to(device).eval()
