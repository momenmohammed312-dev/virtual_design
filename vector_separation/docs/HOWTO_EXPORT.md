# How to Export (إرشادات التصدير)

- الهدف: توفير خطوات عملية لتصدير ملفات فيكتور من Illustrator/Inkscape/SVG generator مع الحفاظ على طبقات الهاف تون والريجستريشن ماركس.
- الخطوات الأساسية:
  1. تحقق من وجود الطبقات: plate_Red.svg, plate_Blue.svg, plate_Green.svg ضمن vector_separation/plates.
  2. تأكد من وجود reg_marks.svg في vector_separation/registration_marks.
  3. احفظ كـ SVG/AI مع احتفاظ بالطبقات، وتحقق من عدم دمج الطبقات إلى Raster.
  4. توليد colors.json وlegend.md كمرجع ثنائي اللغة.
  5. ضع ملف HOWTO_EXPORT.md في docs كمرجع للمطبعة.

- أمور للتحقق قبل التسليم:
  - قياسات المستند النهائي ومكان وضع الهاف تون ومربعات الوجود.
  - توافق اللون مع ألوان CMYK أو spot colors حسب الطلب.
