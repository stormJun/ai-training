require "base64"
require "cgi"
require "fileutils"
require "nokogiri"

source_path, html_path, image_dir, image_prefix = ARGV
abort "usage: #{$PROGRAM_NAME} SOURCE OUTPUT_HTML IMAGE_DIR IMAGE_PREFIX" unless image_prefix

source = File.binread(source_path)
document = Nokogiri::HTML.parse(source, nil, "UTF-8")
article = document.at_css("#js_content")
abort "Could not find the WeChat article body (#js_content)" unless article

title = document.at_css("#activity-name")&.text&.strip
author = document.at_css("#js_name")&.text&.strip
published_at = document.at_css("#publish_time")&.text&.strip
source_url = source[/url:\s+(https?:\/\/[^\s]+)/, 1]
abort "Could not find the article title" if title.nil? || title.empty?

FileUtils.mkdir_p(image_dir)
extensions = {
  "image/gif" => ".gif",
  "image/jpeg" => ".jpg",
  "image/png" => ".png",
  "image/webp" => ".webp"
}

article.css("img").each_with_index do |image, index|
  embedded = image["src"]&.match(/\Adata:([^;,]+)(?:;[^,]*)?;base64,(.+)\z/m)
  abort "Image #{index + 1} is not embedded in the source document" unless embedded

  extension = extensions.fetch(embedded[1]) do
    abort "Unsupported embedded image type: #{embedded[1]}"
  end
  filename = format("image-%02d%s", index + 1, extension)
  File.binwrite(File.join(image_dir, filename), Base64.decode64(embedded[2]))

  image.attributes.each_key { |name| image.remove_attribute(name) }
  image["src"] = File.join(image_prefix, filename)
  image["alt"] = "图 #{index + 1}"
end

# The document title is inserted separately, so retain one top-level heading.
(1..5).to_a.reverse_each do |level|
  article.css("h#{level}").each { |heading| heading.name = "h#{level + 1}" }
end

article.xpath(".//text()[normalize-space(.) = '❝']").remove

article.css("img").each do |image|
  retained = image.attributes.slice("src", "alt")
  image.attributes.each_key { |name| image.remove_attribute(name) }
  retained.each { |name, attribute| image[name] = attribute.value }
end

article.css("a").each do |link|
  retained = link.attributes.slice("href", "title")
  link.attributes.each_key { |name| link.remove_attribute(name) }
  retained.each { |name, attribute| link[name] = attribute.value }
end

article.xpath(".//*").each do |node|
  next if node.name == "img" || node.name == "a"
  node.attributes.each_key { |name| node.remove_attribute(name) }
end

article.css("span, section, figure").reverse_each do |wrapper|
  wrapper.children.each { |child| wrapper.add_previous_sibling(child) }
  wrapper.remove
end

metadata = []
metadata << "<p>作者：#{CGI.escapeHTML(author)}</p>" unless author.nil? || author.empty?
metadata << "<p>发布时间：#{CGI.escapeHTML(published_at)}</p>" unless published_at.nil? || published_at.empty?
if source_url
  escaped_url = CGI.escapeHTML(source_url)
  metadata << "<p>原文：<a href=\"#{escaped_url}\">#{escaped_url}</a></p>"
end

clean_html = <<~HTML.gsub("\u00A0", " ")
  <!doctype html>
  <html lang="zh-CN">
  <head><meta charset="UTF-8"><title>#{CGI.escapeHTML(title)}</title></head>
  <body>
  <h1>#{CGI.escapeHTML(title)}</h1>
  #{metadata.join("\n")}
  <hr>
  #{article.inner_html}
  </body>
  </html>
HTML

File.binwrite(html_path, clean_html)
