from dataclasses import dataclass

@dataclass
class LogCtxData:
    txtENG: str = ""
    txtCN: str = ""
    detail: str = ""

    @property
    def source(self) -> str:
        return self.txtENG or self.txtCN
    
    @property
    def source_lang(self) -> str:
        return "EN" if self.txtENG else "CN"