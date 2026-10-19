package com.dailylingo.app;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.util.TypedValue;
import android.view.View;

/**
 * 启动页：在网页还没有加载出来时显示，避免一片空白。
 * 中间是渐变艺术字 {@code Lingo}，下面有跳动的音量条与状态文字。
 *
 * <p>与桌面端 {@code SplashView.cs} 的版式一致，只是尺寸单位换成 dp，
 * 这样在不同 dpi 的手机上比例才对。</p>
 */
final class SplashView extends View {

    private static final String BRAND = "Lingo";

    private final Paint mBrandPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint mShadowPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint mBarPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint mTextPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF mBarBounds = new RectF();

    private final float mDensity;

    private final int mPageBackground;
    private final int mAccent;
    private final int mAccentDeep;
    private final int mAccentLight;
    private final int mMuted;

    private String mStatus = "";
    private String mTagline = "";

    private boolean mAnimating;
    private long mStartNanos;
    private boolean mLoggedSize;

    SplashView(Context context) {
        super(context);

        mDensity = getResources().getDisplayMetrics().density;
        mPageBackground = color(R.color.page_background);
        mAccent = color(R.color.accent);
        mAccentDeep = color(R.color.accent_deep);
        mAccentLight = color(R.color.accent_light);
        mMuted = color(R.color.muted_text);

        mTagline = context.getString(R.string.splash_tagline);

        mBrandPaint.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
        mBrandPaint.setStyle(Paint.Style.FILL);

        mShadowPaint.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
        mShadowPaint.setStyle(Paint.Style.FILL);
        mShadowPaint.setColor(Color.argb(26, Color.red(mAccent), Color.green(mAccent), Color.blue(mAccent)));

        mBarPaint.setStyle(Paint.Style.FILL);

        mTextPaint.setTypeface(Typeface.create("sans-serif", Typeface.NORMAL));
        mTextPaint.setColor(mMuted);

        setBackgroundColor(mPageBackground);
    }

    private int color(int id) {
        return getResources().getColor(id, getContext().getTheme());
    }

    private float dp(float value) {
        return value * mDensity;
    }

    /** 底部那行灰字（例如「正在连接 …」）。 */
    void setStatus(String status) {
        if (mStatus.equals(status)) {
            return;
        }
        mStatus = status;
        invalidate();
    }

    void startAnimation() {
        if (!mAnimating) {
            mAnimating = true;
            mStartNanos = System.nanoTime();
            postInvalidateOnAnimation();
        }
    }

    void stopAnimation() {
        mAnimating = false;
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);

        float width = getWidth();
        float height = getHeight();
        if (width <= 0 || height <= 0) {
            if (!mLoggedSize) {
                mLoggedSize = true;
                Diagnostics.warn("启动页尺寸异常：" + (int) width + "x" + (int) height);
            }
            return;
        }

        if (!mLoggedSize) {
            mLoggedSize = true;
            Diagnostics.info("启动页首帧：" + (int) width + "x" + (int) height);
        }

        float heightDp = height / mDensity;
        float brandSize = dp(clamp(heightDp * 0.13f, 38f, 92f));
        float taglineSize = dp(clamp(heightDp * 0.021f, 9f, 14f));
        float statusSize = dp(clamp(heightDp * 0.019f, 8.5f, 12.5f));

        mBrandPaint.setTextSize(brandSize);
        mShadowPaint.setTextSize(brandSize);
        mTextPaint.setTextSize(taglineSize);

        Paint.FontMetrics brandMetrics = mBrandPaint.getFontMetrics();
        float brandHeight = brandMetrics.descent - brandMetrics.ascent;

        mTextPaint.setTextSize(taglineSize);
        Paint.FontMetrics taglineMetrics = mTextPaint.getFontMetrics();
        float taglineHeight = taglineMetrics.descent - taglineMetrics.ascent;

        mTextPaint.setTextSize(statusSize);
        Paint.FontMetrics statusMetrics = mTextPaint.getFontMetrics();
        float statusHeight = statusMetrics.descent - statusMetrics.ascent;

        // 逐字测宽，以便自己控制字距（Android 没有 letterSpacing 的绘制级控制）。
        float letterSpacing = dp(6f);
        float[] glyphWidths = new float[BRAND.length()];
        float brandWidth = 0f;
        for (int index = 0; index < BRAND.length(); index++) {
            glyphWidths[index] = mBrandPaint.measureText(String.valueOf(BRAND.charAt(index)));
            brandWidth += glyphWidths[index];
        }
        brandWidth += letterSpacing * (BRAND.length() - 1);

        float barArea = dp(40f);
        float gapBrandTagline = brandSize * 0.16f;
        float gapTaglineBars = dp(26f);
        float gapBarsStatus = dp(24f);

        float totalHeight = brandHeight + gapBrandTagline + taglineHeight + gapTaglineBars
                + barArea + gapBarsStatus + statusHeight;
        float top = Math.max(0f, (height - totalHeight) / 2f - height * 0.04f);

        // 1) 品牌艺术字：纵向渐变 + 淡淡的投影。
        float cursor = (width - brandWidth) / 2f;
        float gradientTop = top + brandSize * 0.12f;
        mBrandPaint.setShader(new LinearGradient(
                0f,
                gradientTop,
                0f,
                gradientTop + brandSize * 0.92f,
                mAccentDeep,
                mAccentLight,
                Shader.TileMode.CLAMP));

        float brandBaseline = top - brandMetrics.ascent;
        for (int index = 0; index < BRAND.length(); index++) {
            String glyph = String.valueOf(BRAND.charAt(index));
            canvas.drawText(glyph, cursor, brandBaseline + brandSize * 0.05f, mShadowPaint);
            canvas.drawText(glyph, cursor, brandBaseline, mBrandPaint);
            cursor += glyphWidths[index] + letterSpacing;
        }
        mBrandPaint.setShader(null);

        // 2) 副标题
        float taglineY = top + brandHeight + gapBrandTagline;
        mTextPaint.setTextSize(taglineSize);
        mTextPaint.setColor(mMuted);
        float taglineWidth = mTextPaint.measureText(mTagline);
        canvas.drawText(mTagline, (width - taglineWidth) / 2f, taglineY - taglineMetrics.ascent, mTextPaint);

        // 3) 跳动的音量条（纯装饰，表示「正在加载」）
        float barsTop = taglineY + taglineHeight + gapTaglineBars;
        drawBars(canvas, barsTop, barArea, width);

        // 4) 状态文字
        if (!mStatus.isEmpty()) {
            mTextPaint.setTextSize(statusSize);
            mTextPaint.setColor(mMuted);
            float statusWidth = mTextPaint.measureText(mStatus);
            float statusTop = barsTop + barArea + gapBarsStatus;
            canvas.drawText(mStatus, (width - statusWidth) / 2f, statusTop - statusMetrics.ascent, mTextPaint);
        }

        if (mAnimating) {
            postInvalidateOnAnimation();
        }
    }

    private void drawBars(Canvas canvas, float top, float area, float viewWidth) {
        final int count = 5;
        float barWidth = dp(8f);
        float gap = dp(9f);

        float phase = ((System.nanoTime() - mStartNanos) / 1_000_000_000f) * 2.4f;
        float barsWidth = count * barWidth + (count - 1) * gap;
        float left = (viewWidth - barsWidth) / 2f;
        float baseline = top + area;

        for (int index = 0; index < count; index++) {
            float wave = (float) Math.sin(phase + index * 0.9f);
            float barHeight = dp(10f) + dp(20f) * (0.5f + 0.5f * wave);
            int alpha = (int) clamp(110f + 110f * (0.5f + 0.5f * wave), 60f, 235f);
            int base = index % 2 == 0 ? mAccent : mAccentLight;
            mBarPaint.setColor(Color.argb(alpha, Color.red(base), Color.green(base), Color.blue(base)));

            mBarBounds.set(left + index * (barWidth + gap), baseline - barHeight,
                    left + index * (barWidth + gap) + barWidth, baseline);
            float radius = barWidth / 2f;
            canvas.drawRoundRect(mBarBounds, radius, radius, mBarPaint);
        }
    }

    private static float clamp(float value, float min, float max) {
        return Math.max(min, Math.min(max, value));
    }
}
