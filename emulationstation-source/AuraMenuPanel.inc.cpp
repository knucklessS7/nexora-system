// AURA main-menu presentation. Reuses native rows, callbacks and input handling.
class AuraMenuPanel final : public TextComponent
{
    ImageComponent gear;
    TextComponent title, caption, detail;
public:
    AuraMenuPanel(Window* window, float w, float h) : TextComponent(window), gear(window), title(window), caption(window), detail(window)
    {
        setSize(w,h);
        auto font = "/userdata/themes/aura-7-native/art/fonts/Cabin-Regular.ttf";
        title.setFont(font, int(Renderer::getScreenHeight()*.029f));
        title.setText("M E N U   P R I N C I P A L");title.setColor(0xEAF6FFFF);
        title.setHorizontalAlignment(ALIGN_CENTER);title.setPosition(0,h*.025f);title.setSize(w,h*.08f);
        gear.setImage("/userdata/themes/aura-7-native/art/menu82/settings.svg");
        gear.setOrigin(.5f,.5f);gear.setPosition(w*.835f,h*.38f);gear.setMaxSize(w*.22f,h*.32f);
        caption.setFont(font,int(Renderer::getScreenHeight()*.021f));caption.setText("CONFIGURAÇÕES");
        caption.setColor(0x8CE8FFFF);caption.setHorizontalAlignment(ALIGN_CENTER);
        caption.setPosition(w*.69f,h*.59f);caption.setSize(w*.28f,h*.06f);
        detail.setFont(font,int(Renderer::getScreenHeight()*.016f));detail.setText("Personalize seu sistema,\ncontroles, rede e muito mais.");
        detail.setColor(0xB5D4EBFF);detail.setHorizontalAlignment(ALIGN_CENTER);
        detail.setPosition(w*.70f,h*.71f);detail.setSize(w*.27f,h*.18f);
    }
    void render(const Transform4x4f& parent) override
    {
        Transform4x4f trans=parent*getTransform();Renderer::setMatrix(trans);
        float w=getSize().x(),h=getSize().y();
        Renderer::drawSolidRectangle(-3,-3,w+6,h+6,0x39BFFF28,0x39BFFF38,1.0f,18);
        Renderer::drawSolidRectangle(0,0,w,h,0x5AD8FF55,0x248DE544,1.0f,16);
        Renderer::drawSolidRectangle(2,2,w-4,h-4,0x051D33B8,0x03101DD0,1.0f,14);
        Renderer::drawSolidRectangle(w*.02f,h*.14f,w*.64f,h*.80f,0x03122288,0x03122288,1.0f,10);
        Renderer::drawSolidRectangle(w*.68f,h*.13f,1,h*.80f,0x3B84AA66,0x3B84AA66);
        Renderer::drawSolidRectangle(w*.47f,h*.105f,w*.06f,2,0x36DCFFFF,0x36DCFFFF);
        Renderer::drawSolidRectangle(w*.80f,h*.675f,w*.07f,2,0x36DCFFFF,0x36DCFFFF);
        title.render(trans);gear.render(trans);caption.render(trans);detail.render(trans);
    }
};
