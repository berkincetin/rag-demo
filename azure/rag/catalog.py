"""Seçilebilir sohbet modelleri ve aralarındaki ölçülmüş farklar.

Katalog tek doğruluk kaynağıdır: arayüz menüsünü doldurur ve sunucu tarafındaki
doğrulamayı yapar. İstemciden gelen ad **doğrudan dağıtım adı olarak
kullanılmaz** — önce buradan geçer, tanınmazsa istek reddedilir.

Modeller arası farklar burada bayrak olarak durur, istemcide `if model_id ==`
zinciri olarak değil. Bayrakların tamamı 2026-08-17'de canlı uca sondalanarak
ölçüldü, tahmin edilmedi:

  gpt-5-mini  `max_tokens` → HTTP 400, `max_completion_tokens` isteniyor
  gpt-5-mini  `temperature=0` → HTTP 400, yalnızca varsayılan (1) kabul ediliyor
  gpt-5-mini  tek kısa cevapta 128 reasoning token harcadı — 1024'lük bütçe
              cevabı boş bırakabilirdi, o yüzden sınırı daha yüksek
  Phi-4-mini  Azure OpenAI ucundan sorunsuz çalışıyor ve araç çağırıyor;
              spec'in öngördüğü `azure-ai-inference` bağımlılığı gerekmedi

Kotası olmayan modeller listede kalır ama `deployed=False` ve sebebiyle
işaretlenir — menüde devre dışı görünür, sessizce başarısız olan bir seçenek
bırakılmaz.

## Ölçülmüş cevap kalitesi (gerçek korpus, aynı soru)

"Yıllık izin talebimi nasıl yaparım?" üç modele soruldu. Doğru cevap
`calisan_sss_rehberi.xlsx` satır 4'te ve üçü de o parçayı aldı.

İlk ölçümde (2026-08-17) yalnızca varsayılan model atıflı cevap verebiliyordu:

| Model | Tur | Arama | Atıf | Sonuç |
|---|---|---|---|---|
| gpt-4.1-mini | 2 | 1 | 2 | doğru cevap |
| gpt-5-mini | 6* | 6 | 0 | hiç cevap yazmadı |
| Phi-4-mini-instruct | 2 | 1 | 0 | boş yanıt döndü |

*Tur sınırı 3'ten 6'ya çıkarıldığında da değişmedi.

İkisi de aynı kök nedenin iki yüzüydü: **araç şeması önlerindeyken metin
üretmiyorlar.** `gpt-5-mini` bunun yerine aramayı tekrarlıyor, `Phi-4-mini`
tamamen boş dönüyor (3/3). Toplanan bağlam doğruydu; sorun modelden hiç
cevap istenmemesiydi.

`graph.py`'ye `final_answer` düğümü eklendi: araç şeması geri çekilip aynı
bağlamla bir tur daha isteniyor. Yeniden ölçüm (2026-08-18):

| Model | Tur | Arama | Atıf | Sonuç |
|---|---|---|---|---|
| gpt-4.1-mini | 2 | 1 | 2 | değişmedi — bu yola hiç uğramıyor |
| gpt-5-mini | 3 | 3 | 3 | doğru cevap (~18 sn) |
| Phi-4-mini-instruct | 2 | 1 | 1 | doğru cevap |

Üçü de atıflı cevap verdiği için `quality_warning` alanı artık boş; alan
korunuyor çünkü ileride eklenecek bir modelin ölçümü yine kötü çıkabilir.
"""

from dataclasses import dataclass

AZURE_MODEL_ID = "gpt-4.1-mini"
PROVIDER = "azure_openai"

DEFAULT_CHAT_MODEL = AZURE_MODEL_ID

# Bölüm 1'de ölçüldü: daha yüksek sıcaklıkta model [n] atıf işaretini zaman
# zaman düşürüyor ve atıf kapısı doğru cevabı reddediyor.
_TEMPERATURE = 0.0
_MAX_TOKENS = 1024

# eastus'ta kota sıfır olduğu için dağıtılamayan modeller (ölçüldü:
# `az cognitiveservices usage list -l eastus`). Katalogda kalıyorlar ki menü
# neden seçilemediklerini söyleyebilsin.
_NO_QUOTA = "eastus bölgesinde bu model için kota tanımlı değil"


@dataclass(frozen=True)
class ModelInfo:
    """Menüde görünen bir model."""

    id: str
    provider: str
    label: str
    context_tokens: int | None = None
    local: bool = False


@dataclass(frozen=True)
class ChatModel:
    """Bir sohbet modelinin dağıtım adı ve çağrı sözleşmesi."""

    id: str
    deployment: str
    label: str
    note: str = ""
    deployed: bool = True
    unavailable_reason: str | None = None
    context_tokens: int | None = None

    # Ölçülmüş çağrı farkları.
    max_tokens_param: str = "max_tokens"
    max_tokens: int = _MAX_TOKENS
    supports_temperature: bool = True
    temperature: float = _TEMPERATURE

    # Ölçülmüş cevap kalitesi (aşağıdaki nota bakınız).
    answers_with_citations: bool = True
    quality_warning: str | None = None

    def payload_limits(self) -> dict[str, object]:
        """Bu modele gönderilebilecek sıcaklık/uzunluk alanları."""
        limits: dict[str, object] = {self.max_tokens_param: self.max_tokens}
        if self.supports_temperature:
            limits["temperature"] = self.temperature
        return limits


_CHAT_MODELS: tuple[ChatModel, ...] = (
    ChatModel(
        id="gpt-4.1-mini",
        deployment="gpt-4.1-mini",
        label="GPT-4.1 mini",
        note="Varsayılan — kapı eşikleri bu modelle kalibre edildi",
        context_tokens=128_000,
    ),
    ChatModel(
        id="gpt-5-mini",
        deployment="gpt-5-mini",
        label="GPT-5 mini",
        note="Alternatif — akıl yürüten model, 3 tur arama yapıyor (~18 sn)",
        context_tokens=400_000,
        max_tokens_param="max_completion_tokens",
        max_tokens=4096,
        supports_temperature=False,
    ),
    ChatModel(
        id="Phi-4-mini-instruct",
        deployment="Phi-4-mini-instruct",
        label="Phi-4 mini instruct",
        note="Bütçe — küçük ve hızlı model, cevapları daha kısa",
        context_tokens=128_000,
    ),
    ChatModel(
        id="cohere-command-a",
        deployment="cohere-command-a",
        label="Cohere Command A",
        note="OpenAI dışı",
        deployed=False,
        unavailable_reason=_NO_QUOTA,
    ),
)

_BY_ID = {model.id: model for model in _CHAT_MODELS}

# Menü ve eski `ModelInfo` API'si yalnızca gerçekten dağıtılmış modelleri görür.
_MODELS = tuple(
    ModelInfo(model.id, PROVIDER, model.label, model.context_tokens)
    for model in _CHAT_MODELS
    if model.deployed
)


def list_models() -> list[ModelInfo]:
    """Bu dağıtımın gerçekten kullanabildiği modeller."""
    return list(_MODELS)


def get_model(model_id: str) -> ModelInfo | None:
    """Kimliğe göre model; bu dağıtımın modeli değilse None."""
    return next((model for model in _MODELS if model.id == model_id), None)


def available_chat_models() -> list[ChatModel]:
    """Menünün çizdiği tüm modeller — dağıtılmamış olanlar sebebiyle birlikte."""
    return list(_CHAT_MODELS)


def resolve_chat_model(model_id: str | None) -> ChatModel:
    """Seçimi kataloğa karşı çözer.

    Boş seçim varsayılana düşer. Tanınmayan bir ad `KeyError` yükseltir —
    çağıran bunu 400'e çevirir, çünkü istemciden gelen metin hiçbir koşulda
    dağıtım adı olarak kullanılmamalıdır.
    """
    if not model_id:
        return _BY_ID[DEFAULT_CHAT_MODEL]
    if model_id not in _BY_ID:
        raise KeyError(model_id)
    return _BY_ID[model_id]
