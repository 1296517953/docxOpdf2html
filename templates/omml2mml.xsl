<?xml version="1.0" encoding="UTF-8"?>
<!--
  OMML → MathML XSLT 转换器
  将 Word 的 Office Math Markup Language (OMML) 转为标准 MathML。
  被 docx_converter.py 在转换公式时调用。
  覆盖：分式、根号、上下标、n元运算符、重音、矩阵、分隔符、方框、极限、虚位等。
-->
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
  xmlns="http://www.w3.org/1998/Math/MathML"
  exclude-result-prefixes="m">

  <!-- ═══════════════════════════════════════════════════════════════
       根元素：oMath（行内） / oMathPara（块级）
       ═══════════════════════════════════════════════════════════════ -->

  <!-- 独立的行内公式 → <math display="inline"> -->
  <xsl:template match="m:oMath[not(parent::m:oMathPara)]">
    <math display="inline">
      <xsl:apply-templates />
    </math>
  </xsl:template>

  <!-- 块级公式内部的 m:oMath 不再套一层 <math>，只输出内容 -->
  <xsl:template match="m:oMath[parent::m:oMathPara]">
    <xsl:apply-templates />
  </xsl:template>

  <xsl:template match="m:oMathPara">
    <math display="block">
      <xsl:apply-templates />
    </math>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       Run / 文本
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:r">
    <mrow>
      <xsl:apply-templates />
    </mrow>
  </xsl:template>

  <xsl:template match="m:t">
    <xsl:if test="normalize-space(.) != '' or @xml:space='preserve'">
      <mtext>
        <xsl:value-of select="." />
      </mtext>
    </xsl:if>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       分式 m:f → mfrac
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:f">
    <mfrac>
      <xsl:apply-templates select="m:num/*" />
      <xsl:apply-templates select="m:den/*" />
    </mfrac>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       根式 m:rad → msqrt（无 deg）/ mroot（有 deg）
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:rad">
    <xsl:choose>
      <xsl:when test="m:deg">
        <mroot>
          <xsl:apply-templates select="m:e/*" />
          <mrow>
            <xsl:apply-templates select="m:deg/*" />
          </mrow>
        </mroot>
      </xsl:when>
      <xsl:otherwise>
        <msqrt>
          <xsl:apply-templates select="m:e/*" />
        </msqrt>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       上下标：sSup → msup / sSub → msub / sSubSup → msubsup
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:sSup">
    <msup>
      <xsl:apply-templates select="m:e/*" />
      <xsl:apply-templates select="m:sup/*" />
    </msup>
  </xsl:template>

  <xsl:template match="m:sSub">
    <msub>
      <xsl:apply-templates select="m:e/*" />
      <xsl:apply-templates select="m:sub/*" />
    </msub>
  </xsl:template>

  <xsl:template match="m:sSubSup">
    <msubsup>
      <xsl:apply-templates select="m:e/*" />
      <xsl:apply-templates select="m:sub/*" />
      <xsl:apply-templates select="m:sup/*" />
    </msubsup>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       n 元运算符 m:nary → munderover
       ∑∫∏ 等，上下限位置由 OMML 决定
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:nary">
    <munderover>
      <mo>
        <xsl:call-template name="nary-char" />
      </mo>
      <xsl:apply-templates select="m:sub/*" />
      <xsl:apply-templates select="m:sup/*" />
    </munderover>
  </xsl:template>

  <xsl:template name="nary-char">
    <xsl:choose>
      <xsl:when test="m:chr/@m:val">
        <xsl:text disable-output-escaping="yes">&amp;#x</xsl:text>
        <xsl:value-of select="m:chr/@m:val" />
        <xsl:text>;</xsl:text>
      </xsl:when>
      <xsl:otherwise>∑</xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       重音 m:acc → mover（带有重音符）
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:acc">
    <mover>
      <xsl:apply-templates select="m:e/*" />
      <mo>
        <xsl:call-template name="accent-char" />
      </mo>
    </mover>
  </xsl:template>

  <xsl:template name="accent-char">
    <xsl:choose>
      <xsl:when test="m:chr/@m:val">
        <xsl:text disable-output-escaping="yes">&amp;#x</xsl:text>
        <xsl:value-of select="m:chr/@m:val" />
        <xsl:text>;</xsl:text>
      </xsl:when>
      <xsl:otherwise>̂</xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       横线 m:bar → mover（带有 macron）
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:bar">
    <mover>
      <xsl:apply-templates select="m:e/*" />
      <mo>¯</mo>
    </mover>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       分隔符 m:d → mrow（带括号）
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:d">
    <mrow>
      <mo>
        <xsl:call-template name="delimiter-char">
          <xsl:with-param name="which" select="'beg'" />
        </xsl:call-template>
      </mo>
      <xsl:apply-templates select="m:e/*" />
      <mo>
        <xsl:call-template name="delimiter-char">
          <xsl:with-param name="which" select="'end'" />
        </xsl:call-template>
      </mo>
    </mrow>
  </xsl:template>

  <xsl:template name="delimiter-char">
    <xsl:param name="which" />
    <xsl:variable name="begChar" select="m:dPr/m:begChr/@m:val" />
    <xsl:variable name="endChar" select="m:dPr/m:endChr/@m:val" />
    <xsl:choose>
      <xsl:when test="$which = 'beg' and $begChar">
        <xsl:text disable-output-escaping="yes">&amp;#x</xsl:text>
        <xsl:value-of select="$begChar" />
        <xsl:text>;</xsl:text>
      </xsl:when>
      <xsl:when test="$which = 'end' and $endChar">
        <xsl:text disable-output-escaping="yes">&amp;#x</xsl:text>
        <xsl:value-of select="$endChar" />
        <xsl:text>;</xsl:text>
      </xsl:when>
      <xsl:when test="$which = 'beg'">(</xsl:when>
      <xsl:otherwise>)</xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       对齐方程 m:eqArr → mtable（每个 e 是一行）
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:eqArr">
    <mtable>
      <xsl:for-each select="m:e">
        <mtr>
          <mtd>
            <xsl:apply-templates select="*" />
          </mtd>
        </mtr>
      </xsl:for-each>
    </mtable>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       矩阵 m:m → mtable
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:m">
    <mtable>
      <xsl:apply-templates select="m:mr" />
    </mtable>
  </xsl:template>

  <xsl:template match="m:mr">
    <mtr>
      <xsl:for-each select="m:e">
        <mtd>
          <xsl:apply-templates select="*" />
        </mtd>
      </xsl:for-each>
    </mtr>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       方框 / 分组字符
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:box">
    <menclose notation="box">
      <xsl:apply-templates select="m:e/*" />
    </menclose>
  </xsl:template>

  <xsl:template match="m:borderBox">
    <menclose notation="box">
      <xsl:apply-templates select="m:e/*" />
    </menclose>
  </xsl:template>

  <xsl:template match="m:groupChr">
    <menclose notation="top">
      <xsl:apply-templates select="m:e/*" />
    </menclose>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       极限 m:limLow → munder / m:limUpp → mover
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:limLow">
    <munder>
      <xsl:apply-templates select="m:e/*" />
      <xsl:apply-templates select="m:lim/*" />
    </munder>
  </xsl:template>

  <xsl:template match="m:limUpp">
    <mover>
      <xsl:apply-templates select="m:e/*" />
      <xsl:apply-templates select="m:lim/*" />
    </mover>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       虚位 / 空白
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:phant">
    <mphantom>
      <xsl:apply-templates select="m:e/*" />
    </mphantom>
  </xsl:template>

  <xsl:template match="m:zeroWid">
    <mpadded width="0">
      <xsl:apply-templates />
    </mpadded>
  </xsl:template>

  <xsl:template match="m:zeroAsc">
    <mpadded depth="0">
      <xsl:apply-templates />
    </mpadded>
  </xsl:template>

  <xsl:template match="m:zeroDesc">
    <mpadded height="0">
      <xsl:apply-templates />
    </mpadded>
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       忽略控制 / 参数属性（无视觉影响）
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="m:ctrlPr | m:argPr | m:dPr | m:eqArrPr | m:mPr | m:naryPr">
    <xsl:apply-templates />
  </xsl:template>

  <!-- ═══════════════════════════════════════════════════════════════
       默认：按元素内容继续处理
       ═══════════════════════════════════════════════════════════════ -->

  <xsl:template match="*">
    <xsl:apply-templates />
  </xsl:template>

  <xsl:template match="text()">
    <xsl:value-of select="." />
  </xsl:template>

</xsl:stylesheet>
